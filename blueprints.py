from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, current_app, jsonify, make_response
from functools import wraps
import os
import requests
import humanize
import datetime
from werkzeug.utils import secure_filename
import logging
import secrets
import string

from db import get_connection
from utils import load_excel_data, exportar_datos_completos, send_password_reset_email, verify_reset_token
from flask import send_file

# Configurar logger para este blueprint
logger = logging.getLogger(__name__)

# Crear un Blueprint para las rutas principales
bp = Blueprint('main', __name__)

# --- DECORADORES DE AUTENTICACIÓN ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'danger')
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE LA APLICACIÓN ---

@bp.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash, is_admin, is_active, email_verified FROM usuarios WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not current_app.bcrypt.check_password_hash(user['password_hash'], password):
            flash('Usuario o contraseña incorrectos.', 'danger')
        elif not user['is_active']:
            flash('Tu cuenta está desactivada. Contacta con un administrador.', 'warning')
        elif not user['email_verified']:
            flash('Tu email no ha sido verificado. Por favor, revisa tu correo.', 'warning')
        else:
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('Has iniciado sesión correctamente.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))

    return render_template('login.html')

@bp.route('/health')
def health():
    return 'OK', 200

@bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('main.login'))

@bp.route('/')
@login_required
def index():
    # Obtener filtro de archivo origen de los parámetros de la URL
    filtro_origen = request.args.getlist('origen_archivo')  # Permite múltiples valores
    if not filtro_origen:
        filtro_origen = None  # Mostrar todos los archivos por defecto
    
    # Importamos la función get_statistics desde utils.py que tiene la estructura completa
    from utils import get_statistics as utils_get_statistics
    stats = utils_get_statistics(filtro_origen_archivo=filtro_origen)
    
    response = make_response(render_template('dashboard.html', stats=stats))
    
    # Añadir headers anti-cache para evitar datos desactualizados
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@bp.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    """Página para realizar una reserva de cita."""
    if request.method == 'POST':
        postal_code = request.form.get('postal_code')
        clinics = []
        error = None
        api_url = 'https://tuotempo-apis-production.up.railway.app/api/centros'
        
        if not postal_code:
            error = 'Por favor, introduce un código postal.'
        else:
            try:
                response = requests.get(api_url, params={'cp': postal_code})
                response.raise_for_status()
                data = response.json()
                
                if data.get('success') and data.get('centros'):
                    clinics = data.get('centros')
                else:
                    error = data.get('message', 'No se encontraron clínicas para este código postal.')

            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling clinic API: {e}")
                error = "No se pudo comunicar con el servicio de clínicas."
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                error = "Ocurrió un error inesperado."

        return render_template('reserve.html', clinics=clinics, error=error, postal_code=postal_code)
    
    # GET request
    return render_template('reserve.html', clinics=[], error=None, postal_code='')


@bp.route('/recargar-datos', methods=['GET', 'POST'])
@login_required
def recargar_datos():
    logger.critical(f"--- ACCESO A RECARGAR_DATOS --- MÉTODO: {request.method} ---")
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)

    archivos = []
    for filename in os.listdir(data_dir):
        if filename.endswith(('.xlsx', '.csv')):
            file_path = os.path.join(data_dir, filename)
            file_stats = os.stat(file_path)
            size_str = humanize.naturalsize(file_stats.st_size)
            mod_time = datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%d/%m/%Y %H:%M')
            archivos.append({
                'nombre': filename,
                'tamano': size_str,
                'modificado': mod_time
            })

    historial = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.*, u.username 
            FROM recargas r 
            JOIN usuarios u ON r.usuario_id = u.id 
            ORDER BY r.fecha DESC 
            LIMIT 50
        """)
        historial = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error al obtener historial de recargas: {e}")

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'recargar_existente':
            archivo_nombre = request.form.get('archivo')
            if not archivo_nombre:
                flash('Debes seleccionar un archivo', 'danger')
                return redirect(url_for('main.recargar_datos'))
            archivo_path = os.path.join(data_dir, archivo_nombre)
            # Obtener el nombre del archivo origen del formulario
            origen_archivo_personalizado = request.form.get('origen_archivo', '').strip()
            return ejecutar_recarga(archivo_path, origen_archivo_personalizado)
        elif action == 'subir_archivo':
            if 'archivo' not in request.files or request.files['archivo'].filename == '':
                flash('No se seleccionó ningún archivo', 'danger')
                return redirect(url_for('main.recargar_datos'))
            
            archivo = request.files['archivo']
            if archivo and archivo.filename.endswith(('.xlsx', '.csv')):
                filename = secure_filename(archivo.filename)
                filepath = os.path.join(data_dir, filename)
                archivo.save(filepath)
                flash(f'Archivo {filename} subido correctamente', 'success')
                if request.form.get('recargar_inmediato'):
                    # Obtener el nombre del archivo origen del formulario
                    origen_archivo_personalizado = request.form.get('origen_archivo', '').strip()
                    return ejecutar_recarga(filepath, origen_archivo_personalizado)
            else:
                flash('Formato de archivo no válido.', 'danger')
            return redirect(url_for('main.recargar_datos'))

    return render_template('recargar_datos.html', archivos=archivos, historial=historial)


def ejecutar_recarga(archivo_path, origen_archivo_personalizado=None):
    try:
        connection = get_connection()
        if not connection:
            flash("No se pudo conectar a la base de datos.", "danger")
            return redirect(url_for('main.recargar_datos'))

        # Contar registros existentes antes de la carga
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            registros_previos = cursor.fetchone()[0]
            logger.info(f"Registros existentes en leads: {registros_previos}")
            logger.info(f"Añadiendo nuevos datos desde: {os.path.basename(archivo_path)} (modo aditivo)")
        finally:
            cursor.close()

        # Determinar el nombre del archivo origen
        if origen_archivo_personalizado:
            nombre_archivo_origen = origen_archivo_personalizado.upper()
        else:
            # Extraer nombre del archivo sin extensión para usar como origen
            nombre_archivo_origen = os.path.splitext(os.path.basename(archivo_path))[0].upper()
        
        logger.info(f"Usando archivo origen: {nombre_archivo_origen}")
        resultado_carga = load_excel_data(connection, archivo_path, origen_archivo=nombre_archivo_origen)
        connection.commit() # Forzar el commit para que los datos sean visibles inmediatamente
        
        registros = resultado_carga.get('insertados', 0)
        errores = resultado_carga.get('errores', 0)
        
        # Contar registros totales después de la carga
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            registros_totales = cursor.fetchone()[0]
            logger.info(f"Total de registros después de la carga: {registros_totales}")
        finally:
            cursor.close()
        
        mensaje = f"Carga completada (modo aditivo). Insertados: {registros}. Errores: {errores}. Total en BD: {registros_totales}."

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO recargas (usuario_id, archivo, registros_importados, resultado, mensaje) VALUES (%s, %s, %s, %s, %s)",
                (session['user_id'], os.path.basename(archivo_path), registros, 'ok', mensaje)
            )
        connection.commit()
        flash(mensaje, 'success')

    except Exception as e:
        error_message = f"Error crítico durante la recarga: {str(e)}"
        logger.error(error_message, exc_info=True)
        try:
            conn_err = get_connection()
            if conn_err:
                with conn_err.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO recargas (usuario_id, archivo, registros_importados, resultado, mensaje) VALUES (%s, %s, %s, %s, %s)",
                        (session.get('user_id', -1), os.path.basename(archivo_path), 0, 'error', error_message)
                    )
                conn_err.commit()
                conn_err.close()
        except Exception as e2:
            logger.error(f"No se pudo registrar el error en el historial: {e2}")
        flash(f'Error en la recarga: {error_message}', 'danger')
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            connection.close()
    
    return redirect(url_for('main.recargar_datos'))

@bp.route('/exportar-datos-completos')
@login_required
def exportar_datos_completos_endpoint():
    """Endpoint para descargar el archivo Excel con leads y llamadas."""
    try:
        connection = get_connection()
        success, result = exportar_datos_completos(connection)
        if success:
            filepath = result
            filename = os.path.basename(filepath)
            # Registrar la acción de exportación en el historial
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO recargas (usuario_id, archivo, registros_importados, resultado, mensaje) VALUES (%s, %s, %s, %s, %s)",
                    (session['user_id'], filename, 0, 'export', f'Exportado a {filename}')
                )
            connection.commit()
            # Enviar el archivo directamente al navegador
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            flash(f'Error al exportar los datos: {result}', 'danger')
    except Exception as e:
        logger.error(f"Error en el endpoint de exportación: {e}", exc_info=True)
        flash(f'Ocurrió un error inesperado durante la exportación: {e}', 'danger')
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            connection.close()
            
    return redirect(url_for('main.recargar_datos'))

@bp.route('/eliminar-archivo-origen', methods=['POST'])
@login_required
def eliminar_archivo_origen():
    """Endpoint para eliminar todos los leads de un archivo origen específico."""
    archivo_origen = request.form.get('archivo_origen')
    confirmar = request.form.get('confirmar')
    
    if not archivo_origen:
        flash('Debe especificar el archivo origen a eliminar', 'danger')
        return redirect(url_for('main.recargar_datos'))
    
    if confirmar != 'ELIMINAR':
        flash('Debe escribir ELIMINAR para confirmar la acción', 'danger')
        return redirect(url_for('main.recargar_datos'))
    
    try:
        connection = get_connection()
        if not connection:
            flash("No se pudo conectar a la base de datos.", "danger")
            return redirect(url_for('main.recargar_datos'))

        cursor = connection.cursor()
        
        # Primero contar cuántos leads se van a eliminar
        cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = %s", (archivo_origen,))
        leads_count = cursor.fetchone()[0]
        
        if leads_count == 0:
            flash(f'No se encontraron leads del archivo "{archivo_origen}"', 'warning')
            return redirect(url_for('main.recargar_datos'))
        
        # Eliminar leads del archivo origen
        cursor.execute("DELETE FROM leads WHERE origen_archivo = %s", (archivo_origen,))
        eliminados = cursor.rowcount
        
        # Marcar archivo origen como inactivo
        cursor.execute("""
            UPDATE archivos_origen 
            SET activo = FALSE, 
                descripcion = CONCAT(IFNULL(descripcion, ''), ' - ELIMINADO el ', NOW())
            WHERE nombre_archivo = %s
        """, (archivo_origen,))
        
        connection.commit()
        
        # Registrar en el historial
        mensaje = f"Eliminados {eliminados} leads del archivo '{archivo_origen}'"
        cursor.execute(
            "INSERT INTO recargas (usuario_id, archivo, registros_importados, resultado, mensaje) VALUES (%s, %s, %s, %s, %s)",
            (session['user_id'], archivo_origen, eliminados, 'delete', mensaje)
        )
        connection.commit()
        
        flash(f'Se eliminaron exitosamente {eliminados} leads del archivo "{archivo_origen}"', 'success')
        logger.warning(f"Usuario {session.get('username')} eliminó {eliminados} leads del archivo {archivo_origen}")
        
    except Exception as e:
        error_message = f"Error eliminando archivo {archivo_origen}: {str(e)}"
        logger.error(error_message, exc_info=True)
        if connection:
            connection.rollback()
        flash(error_message, 'danger')
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            connection.close()
    
    return redirect(url_for('main.recargar_datos'))

@bp.route('/leads')
@login_required
def leads():
    search = request.args.get('search', '')
    estado = request.args.get('estado', '')
    con_pack = request.args.get('conPack', '')
    solo_interesados_sin_cita = request.args.get('solo_interesados_sin_cita', '')
    
    conn = get_connection()
    if not conn:
        flash("Error de conexión", "danger")
        return render_template('leads.html', leads=[], search=search, estado=estado, con_pack=con_pack)
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Debug logging
        print(f"DEBUG LEADS FILTER - search: '{search}', estado: '{estado}', con_pack: '{con_pack}'")
        
        # Construir query dinámicamente
        conditions = []
        params = []
        
        # Base query
        query = "SELECT * FROM leads"
        
        # Filtro de búsqueda (teléfono, nombre, o clínica)
        if search:
            conditions.append("(telefono LIKE %s OR telefono2 LIKE %s OR nombre LIKE %s OR apellidos LIKE %s OR nombre_clinica LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param, search_param])
            print(f"DEBUG - Added search condition for: {search}")
        
        # Filtro por estado
        if estado:
            conditions.append("status_level_1 = %s")
            params.append(estado)
            print(f"DEBUG - Added estado condition for: {estado}")

        # Filtro especial: interesados sin cita (útiles positivos sin 'Cita Agendada')
        # Se interpreta como: status_level_1 comienza por 'Útiles Positivos' pero NO es exactamente 'Cita Agendada'
        if solo_interesados_sin_cita == '1':
            conditions.append("(status_level_1 LIKE 'Útiles Positivos%' AND status_level_1 <> 'Cita Agendada')")
            print("DEBUG - Added filter: solo_interesados_sin_cita = 1")
        
        # Filtro por conPack 
        if con_pack:
            if con_pack == '1':
                conditions.append("conPack = 1")
            elif con_pack == '0':
                conditions.append("(conPack = 0 OR conPack IS NULL)")
            print(f"DEBUG - Added conPack condition for: {con_pack}")
        
        # Agregar condiciones WHERE si existen
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Ordenar y limitar
        query += " ORDER BY updated_at DESC, nombre_clinica LIMIT 100"
        
        print(f"DEBUG - Final query: {query}")
        print(f"DEBUG - Params: {params}")
        
        cursor.execute(query, params)
        leads_data = cursor.fetchall()
        
        print(f"DEBUG - Results found: {len(leads_data)}")
        if leads_data:
            print(f"DEBUG - First result: ID {leads_data[0]['id']}, Name: {leads_data[0]['nombre']}")
        return render_template('leads.html', leads=leads_data, search=search, estado=estado, con_pack=con_pack)
    except Exception as e:
        flash(f"Error al obtener leads: {e}", "danger")
        return render_template('leads.html', leads=[], search=search, estado=estado, con_pack=con_pack)
    finally:
        if conn.is_connected():
            conn.close()

@bp.route('/leads/interesados-sin-cita')
@login_required
def leads_interesados_sin_cita():
    """Atajo para listar interesados sin cita desde la web."""
    # Redirige a /leads con el filtro aplicado
    return redirect(url_for('main.leads', solo_interesados_sin_cita='1'))

@bp.route('/clinica/<int:id>')
@login_required
def ver_clinica(id):
    conn = get_connection()
    if not conn:
        flash("Error de conexión", "danger")
        return redirect(url_for('main.leads'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leads WHERE id = %s", (id,))
        clinica = cursor.fetchone()
        if not clinica:
            flash("Clínica no encontrada", "warning")
            return redirect(url_for('main.leads'))
        return render_template('ver_clinica.html', clinica=clinica)
    except Exception as e:
        flash(f"Error al ver la clínica: {e}", "danger")
        return redirect(url_for('main.leads'))
    finally:
        if conn.is_connected():
            conn.close()


# --- DECORADORES Y RUTAS DE ADMINISTRACIÓN ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, email, is_active, is_admin, created_at FROM usuarios ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_users.html', users=users)

@bp.route('/admin/tools')
@login_required
@admin_required
def admin_tools():
    """Página que muestra las herramientas de administración del sistema."""
    return render_template('admin/tools.html')

@bp.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    from flask import current_app
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        is_admin = 'is_admin' in request.form

        if not username or not email:
            flash('El nombre de usuario y el email son obligatorios.', 'danger')
            return render_template('admin_create_user.html')

        # Generar una contraseña aleatoria segura
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(12))
        password_hash = current_app.bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, email, password_hash, is_admin, email_verified) VALUES (%s, %s, %s, %s, %s)",
                (username, email, password_hash, is_admin, True)
            )
            conn.commit()
            flash(f'Usuario {username} creado exitosamente.', 'success')
            return redirect(url_for('main.admin_users'))
        except Exception as e:
            flash(f'Error al crear el usuario: {e}', 'danger')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    return render_template('admin_create_user.html')

@bp.route('/admin/users/<int:user_id>/reset-password', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    # Aquí se generaría un token y se enviaría por email.
    # Por ahora, solo mostramos un mensaje de confirmación.
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT email, username FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        try:
            send_password_reset_email(user['email'], user_id)
            flash(f"Se ha enviado un correo para restablecer la contraseña a {user['username']} ({user['email']}).", 'success')
        except Exception as e:
            logger.error(f"Error al enviar email de reseteo: {e}")
            flash('No se pudo enviar el correo de restablecimiento. Revisa la configuración del servidor de correo.', 'danger')
    else:
        flash('Usuario no encontrado.', 'danger')
    
    return redirect(url_for('main.admin_users'))


# --- REGISTRO DE APIS --- 

def register_apis(app):
    """
    Registra solo las APIs que sabemos que existen y funcionan.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # APIs que sabemos que existen
    existing_apis = [
        ('api_centros', 'centros_api', 'API de centros'),
        ('api_tuotempo', 'tuotempo_api', 'API de TuoTempo'),
        ('api_daemon_status', 'daemon_status_api', 'API de estado del daemon'),
        ('api_railway_verification', 'railway_verification_api', 'API de verificación de Railway'),
        ('api_resultado_llamada', 'resultado_api', 'API de resultado de llamadas'),
        ('api_pearl_calls', 'api_pearl_calls', 'API de llamadas Pearl'),
        ('api_scheduler', 'api_scheduler', 'API del sistema de scheduler'),
    ]
    
    for module_name, blueprint_name, description in existing_apis:
        try:
            module = __import__(module_name, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            # Evitar doble registro del mismo blueprint
            if blueprint.name in app.blueprints:
                logger.warning(f"Blueprint {blueprint.name} ya registrado, se omite")
            else:
                app.register_blueprint(blueprint)
            logger.info(f"{description} registrada correctamente")
        except ImportError as e:
            logger.warning(f"No se pudo importar {module_name}: {e}")
        except AttributeError as e:
            logger.warning(f"No se encontró {blueprint_name} en {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error registrando {description}: {e}")
    
    logger.info("Registro de APIs completado")
@bp.route("/calls-manager")
@login_required
def calls_manager():
    """Página principal del gestor de llamadas automáticas."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener solo una muestra de leads para la carga inicial (paginación)
        limit = 50  # Cargar solo los primeros 50 leads
        cursor.execute("SELECT * FROM leads ORDER BY id DESC LIMIT %s", (limit,))
        calls = cursor.fetchall()
        
        # Obtener valores únicos para los filtros
        cursor.execute("SELECT DISTINCT status_level_1 FROM leads WHERE status_level_1 IS NOT NULL AND status_level_1 != '' ORDER BY status_level_1")
        estados1 = [row['status_level_1'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT status_level_2 FROM leads WHERE status_level_2 IS NOT NULL AND status_level_2 != '' ORDER BY status_level_2")
        estados2 = [row['status_level_2'] for row in cursor.fetchall()]
        
        # Obtener estadísticas rápidas para el dashboard
        cursor.execute("SELECT call_status, COUNT(*) as count FROM leads GROUP BY call_status")
        status_counts = {row['call_status']: row['count'] for row in cursor.fetchall()}
        
        stats = {
            'total': sum(status_counts.values()),
            'pending': status_counts.get('pending', 0),
            'in_progress': status_counts.get('in_progress', 0),
            'completed': status_counts.get('completed', 0),
            'error': status_counts.get('error', 0)
        }
        
        # Obtener archivos disponibles para el filtro
        cursor.execute("""
            SELECT origen_archivo as nombre_archivo, COUNT(*) as total_registros 
            FROM leads 
            WHERE origen_archivo IS NOT NULL 
            GROUP BY origen_archivo 
            ORDER BY total_registros DESC
        """)
        archivos_disponibles = cursor.fetchall()

        # Añadir los filtros a los datos que se pasan al template
        filter_data = {
            'estados1': estados1,
            'estados2': estados2,
            'archivos_disponibles': archivos_disponibles
        }

    except Exception as e:
        logger.error(f"Error al obtener los datos para el gestor de llamadas: {e}")
        flash('No se pudieron cargar los datos de las llamadas. Revise los logs.', 'danger')
        calls = []
        stats = {}
        filter_data = {'estados1': [], 'estados2': []}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            
    return render_template('calls_manager.html', calls=calls, stats=stats, filter_data=filter_data)

@bp.route('/scheduler-config')
@login_required  
def scheduler_config():
    """Página de configuración del scheduler."""
    return render_template('scheduler_config.html')

@bp.route('/admin/update-leads')
@login_required
def update_leads():
    """Página de administración para actualizar leads."""
    return render_template('admin/update_leads.html')

@bp.route('/daemon/status')
@login_required
def daemon_status():
    """Página de monitoreo del daemon de reservas automáticas."""
    return render_template('daemon_status.html')

@bp.route('/admin/railway-verification')
@login_required
def railway_verification():
    """Página de verificación de servicios en Railway."""
    return render_template('railway_verification.html')

@bp.route('/api/search-leads', methods=['GET'])
@login_required
def search_leads():
    """API para buscar leads por teléfono, nombre o apellido."""
    search_term = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    
    if not search_term or len(search_term) < 2:
        return jsonify({'leads': [], 'message': 'Término de búsqueda muy corto'})
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar por teléfono (telefono o telefono2), nombre, apellidos o ID
        query = """
            SELECT id, nombre, apellidos, telefono, telefono2, email, ciudad,
                   status_level_1, status_level_2, call_status, call_priority,
                   last_call_attempt, call_attempts_count, manual_management, updated_at
            FROM leads 
            WHERE (telefono LIKE %s OR telefono2 LIKE %s 
                   OR nombre LIKE %s OR apellidos LIKE %s OR id = %s)
            ORDER BY updated_at DESC
            LIMIT %s
        """
        
        search_pattern = f'%{search_term}%'
        # Intentar convertir a ID numérico, usar 0 si no es un número
        try:
            search_id = int(search_term)
        except ValueError:
            search_id = 0
            
        cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern, search_id, limit))
        leads = cursor.fetchall()
        
        # Formatear fechas para JSON
        for lead in leads:
            if lead.get('last_call_attempt'):
                lead['last_call_attempt'] = lead['last_call_attempt'].strftime('%Y-%m-%d %H:%M:%S')
            if lead.get('updated_at'):
                lead['updated_at'] = lead['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'leads': leads,
            'count': len(leads),
            'message': f'Encontrados {len(leads)} leads'
        })
        
    except Exception as e:
        logger.error(f"Error buscando leads: {e}")
        return jsonify({'error': 'Error en la búsqueda', 'leads': []}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# --- REGISTRO DE APIS ---

# Esta función ha sido combinada con la función register_apis anterior
# para evitar el error de registro duplicado

# Dummy functions to replace utils imports

def get_statistics():
    return {'total_leads': 0, 'active_calls': 0, 'completed_calls': 0}

# Las funciones load_excel_data, exportar_datos_completos, send_password_reset_email y verify_reset_token
# se importan ahora desde utils.py

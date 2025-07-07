from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from functools import wraps
import os
import requests
import humanize
import datetime
from werkzeug.utils import secure_filename
import logging

from db import get_connection
from utils import load_excel_data, exportar_tabla_leads # Asumimos que estas funciones se moverán a utils.py

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
    # Esta función necesitará bcrypt, que debería ser inicializado en la app principal
    # Por ahora, la lógica se mantiene, pero la importación de bcrypt se gestionará en create_app
    from flask import current_app

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Asumimos que bcrypt está disponible a través de current_app
        if user and current_app.bcrypt.check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            flash('Has iniciado sesión correctamente', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            error = 'Usuario o contraseña incorrectos'
    
    return render_template('login.html', error=error)

@bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('main.login'))

@bp.route('/')
@login_required
def index():
    # La función get_statistics() debería estar en utils.py
    from utils import get_statistics
    stats = get_statistics()
    return render_template('dashboard.html', stats=stats)


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
            return ejecutar_recarga(archivo_path)
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
                    return ejecutar_recarga(filepath)
            else:
                flash('Formato de archivo no válido.', 'danger')
            return redirect(url_for('main.recargar_datos'))

    return render_template('recargar_datos.html', archivos=archivos, historial=historial)


def ejecutar_recarga(archivo_path):
    try:
        connection = get_connection()
        if not connection:
            flash("No se pudo conectar a la base de datos.", "danger")
            return redirect(url_for('main.recargar_datos'))

        logger.info(f"Vaciando la tabla 'leads' desde: {os.path.basename(archivo_path)}")
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE leads")
        logger.info("Tabla 'leads' vaciada.")

        resultado_carga = load_excel_data(connection, archivo_path)
        registros = resultado_carga.get('insertados', 0)
        errores = resultado_carga.get('errores', 0)
        mensaje = f"Recarga completada. Insertados: {registros}. Errores: {errores}."

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

@bp.route('/exportar-tabla-leads')
@login_required
def exportar_tabla_leads_endpoint():
    try:
        connection = get_connection()
        success, result = exportar_tabla_leads(connection)
        if success:
            filepath = result
            filename = os.path.basename(filepath)
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO recargas (usuario_id, archivo, registros_importados, resultado, mensaje) VALUES (%s, %s, %s, %s, %s)",
                (session['user_id'], filename, 0, 'export', f'Exportado a {filename}')
            )
            connection.commit()
            cursor.close()
            flash(f'Datos exportados a {filename}', 'success')
        else:
            flash(f'Error al exportar: {result}', 'danger')
        connection.close()
    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'danger')
    return redirect(url_for('main.recargar_datos'))

@bp.route('/leads')
@login_required
def leads():
    search = request.args.get('search', '')
    conn = get_connection()
    if not conn:
        flash("Error de conexión", "danger")
        return render_template('leads.html', leads=[], search=search)
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM leads WHERE nombre_clinica LIKE %s ORDER BY nombre_clinica"
        cursor.execute(query, (f"%{search}%",))
        leads_data = cursor.fetchall()
        return render_template('leads.html', leads=leads_data, search=search)
    except Exception as e:
        flash(f"Error al obtener leads: {e}", "danger")
        return render_template('leads.html', leads=[], search=search)
    finally:
        if conn.is_connected():
            conn.close()

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

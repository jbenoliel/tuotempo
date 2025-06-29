from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
import os
import logging
import requests
from io import BytesIO
import re
from dotenv import load_dotenv

from config import settings
from db import get_connection

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY

# URL del archivo Excel en GitHub
EXCEL_URL = (
    "https://raw.githubusercontent.com/jbenoliel/tuotempo/main/data.xlsx"
    "?v=" + str(datetime.now().timestamp())
)

@app.route('/')
def index():
    """Página principal del dashboard"""
    # Obtener estadísticas generales
    stats = get_statistics()
    return render_template('index.html', stats=stats)

@app.route('/leads')
def leads():
    """Lista todas las clínicas con filtros opcionales"""
    # Parámetros de filtrado
    search = request.args.get('search', '')
    estado = request.args.get('estado', '')
    con_pack = request.args.get('conPack', '')
    
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "danger")
        return render_template('leads.html', leads=[], search=search, estado=estado, con_pack=con_pack)
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Construir la consulta con filtros
        query = "SELECT * FROM leads WHERE 1=1"
        params = []
        
        if search:
            query += " AND (nombre_clinica LIKE %s OR direccion_clinica LIKE %s OR telefono LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if estado:
            query += " AND ultimo_estado = %s"
            params.append(estado)
        
        if con_pack:
            con_pack_bool = con_pack.lower() in ['true', '1', 't', 'y', 'yes']
            query += " AND conPack = %s"
            params.append(con_pack_bool)
        
        # Ordenar por nombre
        query += " ORDER BY nombre_clinica"
        
        cursor.execute(query, params)
        leads = cursor.fetchall()
        
        # Formatear fechas para visualización
        for clinica in leads:
            # Asume que hay columnas 'nombre' y 'apellidos', si no existen, usa nombre_clinica
            # No modificar los nombres de las columnas, se pasan tal cual vienen de MySQL/Excel
            # Si algún campo requiere formato especial, hazlo aquí, pero usa los nombres reales.
            pass
        
        print('DEBUG leads:', leads)
        return render_template('leads.html', leads=leads, search=search, estado=estado, con_pack=con_pack)
    
    except Error as e:
        flash(f"Error al obtener datos: {e}", "danger")
        return render_template('leads.html', leads=[], search=search, estado=estado, con_pack=con_pack)
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/clinica/<int:id>')
def ver_clinica(id):
    """Ver detalles de una clínica específica"""
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "danger")
        return redirect(url_for('leads'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM leads WHERE id = %s"
        cursor.execute(query, (id,))
        clinica = cursor.fetchone()
        
        if not clinica:
            flash("Clínica no encontrada", "warning")
            return redirect(url_for('leads'))
        
        # Formatear fecha para visualización
        if clinica.get('cita'):
            clinica['cita_formatted'] = clinica['cita'].strftime("%d/%m/%Y %H:%M")
        else:
            clinica['cita_formatted'] = "No programada"
        
        return render_template('detalle_clinica.html', clinica=clinica)
    
    except Error as e:
        flash(f"Error al obtener datos: {e}", "danger")
        return redirect(url_for('leads'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/editar_clinica/<int:id>', methods=['GET', 'POST'])
def editar_clinica(id):
    """Editar información de una clínica"""
    if request.method == 'POST':
        # Procesar el formulario de edición
        nombre = request.form.get('nombre_clinica')
        direccion = request.form.get('direccion_clinica')
        telefono = request.form.get('telefono')
        cita_str = request.form.get('cita')
        con_pack = 'conPack' in request.form
        estado = request.form.get('estado')
        
        conn = get_connection()
        if not conn:
            flash("Error de conexión a la base de datos", "danger")
            return redirect(url_for('leads'))
        
        try:
            cursor = conn.cursor()
            
            # Convertir fecha si se proporciona
            cita = None
            if cita_str and cita_str.strip():
                try:
                    cita = datetime.strptime(cita_str, "%Y-%m-%dT%H:%M")
                except ValueError:
                    flash("Formato de fecha incorrecto", "danger")
                    return redirect(url_for('editar_clinica', id=id))
            
            # Actualizar datos
            query = """
            UPDATE leads 
            SET nombre_clinica = %s, direccion_clinica = %s, telefono = %s, 
                cita = %s, conPack = %s, ultimo_estado = %s
            WHERE id = %s
            """
            cursor.execute(query, (nombre, direccion, telefono, cita, con_pack, estado, id))
            conn.commit()
            
            flash("Clínica actualizada correctamente", "success")
            return redirect(url_for('ver_clinica', id=id))
        
        except Error as e:
            flash(f"Error al actualizar datos: {e}", "danger")
            return redirect(url_for('editar_clinica', id=id))
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    else:
        # Mostrar formulario de edición
        conn = get_db_connection()
        if not conn:
            flash("Error de conexión a la base de datos", "danger")
            return redirect(url_for('leads'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM leads WHERE id = %s"
            cursor.execute(query, (id,))
            clinica = cursor.fetchone()
            
            if not clinica:
                flash("Clínica no encontrada", "warning")
                return redirect(url_for('leads'))
            
            # Formatear fecha para el input datetime-local
            if clinica.get('cita'):
                clinica['cita_input'] = clinica['cita'].strftime("%Y-%m-%dT%H:%M")
            else:
                clinica['cita_input'] = ""
            
            return render_template('editar_clinica.html', clinica=clinica)
        
        except Error as e:
            flash(f"Error al obtener datos: {e}", "danger")
            return redirect(url_for('leads'))
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

@app.route('/exportar_excel')
def exportar_excel():
    """Exportar datos a Excel"""
    conn = get_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "danger")
        return redirect(url_for('leads'))
    
    try:
        # Obtener datos
        df = pd.read_sql("SELECT * FROM leads", conn)
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"segurcaixa_leads_{timestamp}.xlsx"
        filepath = os.path.join("static", "exports", filename)
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Guardar Excel
        df.to_excel(filepath, index=False)
        
        # Devolver enlace de descarga
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": url_for('static', filename=f'exports/{filename}')
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
    finally:
        if conn.is_connected():
            conn.close()

def get_statistics():
    """Obtener estadísticas generales para el dashboard"""
    stats = {
        'total_leads': 0,
        'citas_programadas': 0,
        'con_pack': 0,
        'estados': {
            'no_answer': 0,
            'busy': 0,
            'completed': 0,
            'sin_estado': 0
        }
    }
    
    conn = get_connection()
    if not conn:
        return stats
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Total de clínicas
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        result = cursor.fetchone()
        stats['total_leads'] = result['total'] if result else 0
        
        # Citas programadas
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE cita IS NOT NULL")
        result = cursor.fetchone()
        stats['citas_programadas'] = result['total'] if result else 0
        
        # Con pack
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE conPack = TRUE")
        result = cursor.fetchone()
        stats['con_pack'] = result['total'] if result else 0
        
        # Estados
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado = 'no answer'")
        result = cursor.fetchone()
        stats['estados']['no_answer'] = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado = 'busy'")
        result = cursor.fetchone()
        stats['estados']['busy'] = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado = 'completed'")
        result = cursor.fetchone()
        stats['estados']['completed'] = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado IS NULL")
        result = cursor.fetchone()
        stats['estados']['sin_estado'] = result['total'] if result else 0
        
        return stats
    
    except Error as e:
        print(f"Error al obtener estadísticas: {e}")
        return stats
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

import locale

# Intentar poner el locale a español para los nombres de días y meses
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        pass  # Si falla, usará inglés

def fecha_humana(fecha_str, hora_str):
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
    dia_semana = fecha.strftime("%A")  # Ej: 'martes'
    dia = fecha.day
    mes = fecha.strftime("%B")         # Ej: 'julio'
    # Capitaliza el día de la semana
    return f"{dia_semana.capitalize()} {dia} de {mes} a las {hora_str}"

@app.route('/test_citas')
def test_citas():
    return render_template('test_citas.html')

@app.route('/api/proponer_citas', methods=['POST'])
def proponer_citas():
    data = request.get_json()
    # Recoge solo pares completos
    fechas_horas_raw = []
    for i in range(1, 4):
        f = data.get(f'fecha{i}')
        h = data.get(f'hora{i}')
        if f and h:
            fechas_horas_raw.append((f, h))
    if not fechas_horas_raw:
        return jsonify({"respuesta": "Debe proporcionar al menos una fecha y hora."}), 400
    agrupadas = {}
    for fecha, hora in fechas_horas_raw:
        if fecha not in agrupadas:
            agrupadas[fecha] = []
        agrupadas[fecha].append(hora)
    partes = []
    for fecha, horas in agrupadas.items():
        fecha_fmt = fecha_humana(fecha, horas[0]).split(' a las')[0]
        if len(horas) == 1:
            partes.append(f"el {fecha_fmt} a las {horas[0]}")
        else:
            horas_txt = ' y a las '.join(horas)
            partes.append(f"el {fecha_fmt} a las {horas_txt}")
    if len(partes) == 1:
        respuesta = f"Puedo proponer {partes[0]}. ¿Le viene bien?"
    elif len(partes) == 2:
        respuesta = f"Puedo proponer {partes[0]} o {partes[1]}. ¿Cuál le viene mejor?"
    else:
        respuesta = f"Puedo proponer {', '.join(partes[:-1])} o {partes[-1]}. ¿Cuál le viene mejor?"
    return jsonify({"respuesta": respuesta})

@app.route('/test')
def test():
    return "¡Funciona en Railway!"

@app.route('/api/clinica/code', methods=['GET'])
def buscar_codigo_clinica():
    """Buscar el código de una clínica en función del nombre o de la dirección."""
    q = request.args.get('q', '').strip()
    campo = request.args.get('campo', '').strip().lower()
    if not q or campo not in ('nombre', 'direccion'):
        return (
            jsonify({
                'error': 'Debe proporcionar parámetros q y campo (campo=nombre o campo=direccion)'
            }),
            400,
        )
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        columna = 'areaTitle' if campo == 'nombre' else 'address'
        sql = (
            f"SELECT areaid AS code, areaTitle AS nombre, address "
            f"FROM clinicas WHERE {columna} LIKE %s LIMIT 3"
        )
        like_param = f"%{q}%"
        cursor.execute(sql, (like_param,))
        resultados = cursor.fetchall()
        return jsonify({'results': resultados})
    finally:
        cursor.close()
        conn.close()

def init_database():
    """Inicializa la base de datos y crea las tablas necesarias si no existen"""
    try:
        # Conectar a la base de datos
        connection = get_connection()
        logger.info("¡Conexión exitosa a MySQL!")
        cursor = connection.cursor()
        
        # Verificar si la tabla leads ya existe
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            logger.info(f"La tabla 'leads' ya existe. Total registros: {count}")
        except mysql.connector.Error as err:
            if err.errno == 1146:  # Table doesn't exist
                logger.info("La tabla 'leads' no existe. Creándola...")
                # Crear tabla leads
                create_table_query = (
                    "CREATE TABLE leads ("
                    "id INT AUTO_INCREMENT PRIMARY KEY,"
                    "nombre VARCHAR(100),"
                    "apellidos VARCHAR(150),"
                    "nombre_clinica VARCHAR(255),"
                    "direccion_clinica VARCHAR(255),"
                    "codigo_postal VARCHAR(10),"
                    "ciudad VARCHAR(100),"
                    "telefono VARCHAR(20),"
                    "area_id VARCHAR(100),"
                    "match_source VARCHAR(50),"
                    "match_confidence INT,"
                    "cita DATETIME NULL,"
                    "conPack BOOLEAN DEFAULT FALSE,"
                    "ultimo_estado ENUM('no answer', 'busy', 'completed') NULL"
                    ")"
                )
                
                cursor.execute(create_table_query)
                logger.info("Tabla 'leads' creada correctamente")
            else:
                logger.error(f"Error al verificar tabla leads: {err}")
                raise
        
        # Verificar tablas disponibles y crear/clasificar tabla 'clinicas'
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        logger.info(f"Tablas disponibles en la base de datos: {tables}")

        # Crear tabla 'clinicas' si no existe y cargar desde Excel si está vacía
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clinicas (
                    areaid VARCHAR(255) PRIMARY KEY,
                    areaTitle VARCHAR(255),
                    address TEXT,
                    cp VARCHAR(10),
                    city VARCHAR(100),
                    province VARCHAR(100)
                )
                """
            )
            logger.info("Tabla 'clinicas' creada correctamente o ya existía")
            cursor.execute("SELECT COUNT(*) FROM clinicas")
            count_clinicas = cursor.fetchone()[0]
            if count_clinicas == 0:
                df = pd.read_excel('centros_exportados.xlsx')
                records = df[['areaid', 'areaTitle', 'address', 'cp', 'city', 'province']].astype(str).values.tolist()
                insert_q = (
                    "INSERT INTO clinicas (areaid, areaTitle, address, cp, city, province)"
                    " VALUES (%s, %s, %s, %s, %s, %s)"
                )
                cursor.executemany(insert_q, records)
                connection.commit()
                logger.info(f"Cargadas {len(records)} clínicas en la tabla 'clinicas'.")
        except Exception as err:
            logger.error(f"Error creando o cargando clínicas: {err}")

        # Asegurar columna para almacenar resultado de la llamada en leads
        try:
            cursor.execute("SHOW COLUMNS FROM leads LIKE 'resultado_llamada'")
            if cursor.fetchone() is None:
                cursor.execute(
                    "ALTER TABLE leads ADD COLUMN resultado_llamada "
                    "ENUM('volver a marcar','no interesado','cita sin pack','cita con pack') NULL"
                )
                logger.info("Columna 'resultado_llamada' añadida a la tabla 'leads'")
            # Asegurar columna telefono2
            cursor.execute("SHOW COLUMNS FROM leads LIKE 'telefono2'")
            if cursor.fetchone() is None:
                cursor.execute(
                    "ALTER TABLE leads ADD COLUMN telefono2 VARCHAR(20) NULL"
                )
                logger.info("Columna 'telefono2' añadida a la tabla 'leads'")
        except Exception as err:
            logger.error(f"Error asegurando columnas en leads: {err}")

        # Cerrar conexión
        cursor.close()
        connection.close()
        logger.info("Conexión cerrada")
        return True
    except Exception as e:
        logger.error(f"Error en init_database: {e}")
        return False

def load_excel_data(connection, excel_url):
    """Carga datos desde un archivo Excel a la tabla leads"""
    try:
        logger.info(f"Descargando Excel desde URL: {excel_url}")
        try:
            response = requests.get(excel_url, timeout=30)
            if response.status_code != 200:
                error_msg = f"Error al descargar el Excel: {response.status_code}"
                logger.error(error_msg)
                return False, error_msg
            
            excel_data = response.content
            logger.info(f"Excel descargado correctamente: {len(excel_data)} bytes")
        except Exception as download_err:
            error_msg = f"Error al descargar el archivo: {str(download_err)}"
            logger.error(error_msg)
            return False, error_msg
        
        # Leer el Excel desde los bytes descargados
        df = pd.read_excel(BytesIO(excel_data))
        logger.info(f"Excel leído exitosamente. {len(df)} filas encontradas.")
        
        # Truncar la tabla para evitar duplicados
        cursor = connection.cursor()
        logger.info("Truncando tabla leads...")
        cursor.execute("TRUNCATE TABLE leads")
        
        # Preparar los datos para inserción
        records = []
        for _, row in df.iterrows():
            nombre = str(row.get('NOMBRE', ''))
            apellidos = str(row.get('APELLIDOS', ''))
            # Extraer código postal y ciudad de la dirección si es posible
            direccion = str(row.get('DIRECCION_CLINICA', ''))
            codigo_postal = ''
            ciudad = ''
            
            # Intentar extraer código postal (formato español: 5 dígitos)
            cp_match = re.search(r'\b\d{5}\b', direccion)
            if cp_match:
                codigo_postal = cp_match.group(0)
            
            # Asignar teléfonos exactamente según columnas
            telefono = str(row.get('TELEFONO1', '')).strip() if 'TELEFONO1' in df.columns and pd.notna(row.get('TELEFONO1', '')) else ''
            telefono2 = str(row.get('TELEFONO2', '')).strip() if 'TELEFONO2' in df.columns and pd.notna(row.get('TELEFONO2', '')) else ''
            
            # Buscar columna de fecha de cita si existe
            cita_columns = ['FECHA_CITA', 'CITA', 'FECHA', 'DATE']
            cita_value = None
            for col in cita_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    cita_value = row.get(col)
                    break
            
            # Buscar columna de pack si existe
            pack_columns = ['PACK', 'CONPACK', 'CON_PACK']
            pack_value = False
            for col in pack_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    # Convertir a booleano (True si es 1, 'SI', 'S', 'TRUE', etc.)
                    pack_str = str(row.get(col)).strip().upper()
                    pack_value = pack_str in ['1', 'TRUE', 'SI', 'S', 'YES', 'Y', 'VERDADERO', 'V']
                    break
            
            # Buscar columna de estado si existe
            estado_columns = ['ESTADO', 'STATUS', 'ULTIMO_ESTADO']
            estado_value = None
            for col in estado_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    estado_str = str(row.get(col)).strip().lower()
                    # Normalizar valores de estado
                    if 'no answer' in estado_str or 'noanswer' in estado_str or 'no' in estado_str:
                        estado_value = 'no answer'
                    elif 'busy' in estado_str or 'ocupado' in estado_str:
                        estado_value = 'busy'
                    elif 'complete' in estado_str or 'completado' in estado_str or 'finalizado' in estado_str:
                        estado_value = 'completed'
                    break
            
            record = (
                nombre,
                apellidos,
                row.get('NOMBRE_CLINICA', ''),
                direccion,
                codigo_postal,
                ciudad,
                telefono,
                telefono2,
                row.get('areaId', ''),
                row.get('match_source', ''),
                row.get('match_confidence', 0),
                cita_value,
                pack_value,
                estado_value
            )
            records.append(record)
        
        # Insertar los datos
        insert_query = """
        INSERT INTO leads (
            nombre, apellidos, nombre_clinica, direccion_clinica, codigo_postal, ciudad, telefono, telefono2,
            area_id, match_source, match_confidence, cita, conPack, ultimo_estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        logger.info(f"Insertando {len(records)} registros en la tabla leads...")
        cursor.executemany(insert_query, records)
        connection.commit()
        
        logger.info(f"Se insertaron {cursor.rowcount} registros en la tabla 'leads'")
        
        # Verificar que se insertaron los datos
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        logger.info(f"Total registros en leads después de la inserción: {count}")
        
        cursor.close()
        return True, "Datos cargados exitosamente"
    except Exception as e:
        error_msg = f"Error al cargar datos: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

@app.route('/admin/load-excel')
def admin_load_excel():
    """Endpoint para cargar datos del Excel a la base de datos"""
    try:
        # Conectar a la base de datos
        connection = get_connection()
        
        # Verificar si la tabla leads ya existe
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            logger.info(f"La tabla 'leads' existe. Total registros: {count}")
        except mysql.connector.Error as err:
            if err.errno == 1146:  # Table doesn't exist
                logger.info("La tabla 'leads' no existe. Inicializando la base de datos...")
                cursor.close()
                connection.close()
                # Inicializar la base de datos primero
                if not init_database():
                    return jsonify({'success': False, 'message': 'Error al inicializar la base de datos'}), 500
                
                # Reconectar
                connection = get_connection()
            else:
                logger.error(f"Error al verificar tabla leads: {err}")
                return jsonify({'success': False, 'message': f'Error de base de datos: {err}'}), 500
        
        # Cargar datos del Excel
        success, message = load_excel_data(connection, EXCEL_URL)
        connection.close()
        
        if success:
            return jsonify({
                'success': True, 
                'message': message
            })
        else:
            return jsonify({
                'success': False, 
                'message': message
            }), 500
    except Exception as e:
        logger.error(f"Error en admin_load_excel: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/recargar-excel')
def recargar_excel_endpoint():
    """Endpoint para recargar datos del Excel usando el script centralizado"""
    try:
        # Importamos aquí para evitar referencias circulares
        from recargar_excel import recargar_excel
        
        # Llamamos a la función centralizada
        success, message = recargar_excel()
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    except Exception as e:
        logger.error(f"Error al recargar Excel: {e}")
        return jsonify({
            'success': False,
            'message': f"Error al recargar Excel: {str(e)}"
        }), 500

# Inicializar la base de datos al arrancar la aplicación
init_database()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

import mysql.connector
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from config import settings
import mysql.connector

# Cargar variables de entorno si existe un archivo .env
load_dotenv()

# El logger será configurado por la aplicación principal
logger = logging.getLogger(__name__)

# Crear un Blueprint en lugar de una app. Todas las rutas aquí definidas
# colgarán del prefijo /api que se registra en la app principal.
resultado_api = Blueprint('resultado_api', __name__)

# Configuración de la base de datos usando settings
DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_DATABASE
}

def get_db_connection():
    """Establece conexión con la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Error al conectar a MySQL: {err}")
        return None

@resultado_api.route('/api/status', methods=['GET'])
def status():
    """Endpoint para verificar el estado de la API"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service": "API Resultado Llamada"
    })

@resultado_api.route('/api/actualizar_resultado', methods=['POST'])
def actualizar_resultado():
    """
    Actualiza el resultado y los datos de una llamada para un lead específico.
    Este endpoint recibe datos de la llamada desde un sistema externo (como NLPearl) y los guarda en la BD.
    """
    data = request.json
    logger.info(f"Recibida petición para actualizar resultado: {data}")

    # Validar datos requeridos
    if not data or not data.get('telefono'):
        logger.error("Petición rechazada: No se proporcionó número de teléfono.")
        return jsonify({"error": "Se requiere el número de teléfono"}), 400

    telefono = data.get('telefono')

    # -------------------------------------------------------------
    # 1. Extracción de parámetros adicionales y reglas de negocio
    # -------------------------------------------------------------
    buzon = data.get('buzon')                      # True si se cayó en buzón
    volver_a_llamar_flag = data.get('volverALlamar')  # True si se debe volver a llamar

    codigo_no_interes = data.get('codigoNoInteres')
    codigo_volver_llamar = data.get('codigoVolverLlamar')

    # Mapas de traducción de códigos compactos → descripciones
    mapa_no_interes = {
        'no disponibilidad': 'no disponibilidad cliente',
        'descontento': 'Descontento con Adeslas',
        'bajaProxima': 'Próxima baja',
        'otros': 'No da motivos'
    }

    mapa_volver_llamar = {
        'buzon': 'buzón',
        'interrupcion': 'no disponible cliente',
        'proble tecnico': 'Interesado. Problema técnico',
        'proble_tecnico': 'Interesado. Problema técnico'
    }

    # -------------------------------------------------------------
    # 2. Deducción automática de status_level_1 y status_level_2
    # -------------------------------------------------------------
    status_level_1 = None
    status_level_2 = None

    if data.get('nuevaCita'):
        # Una nueva cita siempre se considera un Éxito
        status_level_1 = 'Éxito'
        status_level_2 = 'Cita programada'
    elif buzon:
        status_level_1 = 'Volver a llamar'
        status_level_2 = 'buzón'
    elif volver_a_llamar_flag:
        status_level_1 = 'Volver a llamar'
        status_level_2 = data.get('razonvueltaallamar') or 'Pendiente'
    elif data.get('noInteresado') or codigo_no_interes in mapa_no_interes:
        status_level_1 = 'No Interesado'
        # Tomamos razón del mapa si existe, o texto libre proporcionado
        status_level_2 = mapa_no_interes.get(codigo_no_interes, data.get('razonNoInteres'))
    elif codigo_volver_llamar in mapa_volver_llamar:
        status_level_1 = 'Volver a llamar'
        status_level_2 = mapa_volver_llamar[codigo_volver_llamar]
    elif data.get('conPack'):
        status_level_1 = 'Éxito'
        status_level_2 = 'Contratado'
    elif data.get('errorTecnico'):
        status_level_1 = 'Volver a llamar'
        status_level_2 = 'Interesado. Problema técnico'

    # -------------------------------------------------------------
    # 3. Construcción de diccionario de actualización
    # -------------------------------------------------------------
    # Forzar strip en status levels si existen
    if status_level_1:
        status_level_1 = status_level_1.strip()
    if status_level_2:
        status_level_2 = status_level_2.strip()

    update_fields = {
        'status_level_1': status_level_1,
        'status_level_2': status_level_2,
        'conPack': data.get('conPack'),
        'hora_rellamada': data.get('horaRellamada'),
        'error_tecnico': data.get('errorTecnico'),
        'razon_vuelta_a_llamar': data.get('razonvueltaallamar'),
        'razon_no_interes': data.get('razonNoInteres')
    }

    # Si llega una nueva cita, actualizamos los campos 'cita' (DATE) y opcionalmente 'hora_cita' (TIME)
    if data.get('nuevaCita'):
        try:
            # Intentar convertir el formato de fecha recibido (DD/MM/YYYY) a formato SQL (YYYY-MM-DD)
            fecha_str = data.get('nuevaCita')
            # Detectar el formato de la fecha recibida
            if '/' in fecha_str:
                # Formato DD/MM/YYYY
                dia, mes, anio = fecha_str.split('/')
                fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            else:
                # Asumir que ya viene en formato YYYY-MM-DD
                fecha_formateada = fecha_str
            
            # Guardar la fecha en la columna 'cita'
            update_fields['cita'] = fecha_formateada

            # Si también viene la hora de la cita, la guardamos en 'hora_cita'
            if data.get('horaCita'):
                hora_str = data.get('horaCita')
                # Asegurar formato HH:MM:SS
                if len(hora_str.split(':')) == 2:
                    hora_str += ':00'
                update_fields['hora_cita'] = hora_str

            # --- Ajustar automáticamente los status al recibir una cita ---
            update_fields['status_level_1'] = 'Cita Agendada'
            con_pack_val = data.get('conPack')
            if con_pack_val is not None:
                try:
                    truthy = str(con_pack_val).lower() in ['1', 'true', 'yes', 'si', 'sí', 'on']
                except Exception:
                    truthy = False
                update_fields['status_level_2'] = 'Con Pack' if truthy else 'Sin Pack'
        except Exception as e:
            logger.error(f"Error al procesar la fecha de cita: {e}")
            return jsonify({"error": f"Formato de fecha inválido: {data.get('nuevaCita')}. Use DD/MM/YYYY."}), 400

    # -------------------------------------------------------------
    # 4. Filtrar valores None para no sobreescribir con nulos
    # -------------------------------------------------------------

    # Filtrar campos que son None para no sobreescribir datos existentes con nulos en la BD
    update_data = {k: v for k, v in update_fields.items() if v is not None}

    if not update_data:
        return jsonify({"error": "No se proporcionaron datos para actualizar"}), 400

    # Construir la consulta SQL dinámicamente
    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    sql_query = f"UPDATE leads SET {set_clause} WHERE telefono = %s"
    
    values = list(update_data.values())
    values.append(telefono)

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(sql_query, tuple(values))

        if cursor.rowcount == 0:
            logger.warning(f"No se encontró ningún lead con el teléfono: {telefono}")
            return jsonify({"error": f"No se encontró ningún lead con el teléfono {telefono}"}), 404

        conn.commit()
        logger.info(f"Lead con teléfono {telefono} actualizado correctamente. {cursor.rowcount} fila(s) afectada(s).")

        return jsonify({
            "success": True,
            "message": f"Lead {telefono} actualizado correctamente."
        })

    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos al actualizar el lead {telefono}: {err}")
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@resultado_api.route('/api/obtener_resultados', methods=['GET'])
def obtener_resultados():
    """
    Obtener contactos filtrados por resultado de llamada
    """
    # Parámetro opcional de filtrado
    resultado = request.args.get('resultado')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, nombre, apellidos, telefono, cita, conPack, resultado_llamada FROM leads WHERE 1=1"
        params = []
        
        if resultado:
            query += " AND resultado_llamada = %s"
            params.append(resultado)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convertir datetime a string para JSON
        for row in results:
            if row.get('cita'):
                row['cita'] = row['cita'].strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "success": True,
            "count": len(results),
            "contactos": results
        })
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import json
import re
import logging
import mysql.connector
from tuotempo import Tuotempo

# Crear el Blueprint para la API de Tuotempo
tuotempo_api = Blueprint('tuotempo_api', __name__)

# --- Funciones de Utilidad ---
def _norm_phone(phone: str) -> str:
    """Normaliza un número de teléfono eliminando caracteres no numéricos."""
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)

def _get_db_connection():
    """Obtiene una conexión a la base de datos MySQL."""
    try:
        # Configuración de la base de datos (misma que en api_resultado_llamada.py)
        DB_CONFIG = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'tuotempo'),
            'ssl_disabled': True,
            'autocommit': True,
            'charset': 'utf8mb4',
            'use_unicode': True
        }
        
        # Intentar conexión con SSL deshabilitado
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        current_app.logger.error(f"Error conectando a MySQL: {e}")
        # Fallback: intentar sin SSL explícitamente
        try:
            DB_CONFIG_FALLBACK = DB_CONFIG.copy()
            DB_CONFIG_FALLBACK.pop('ssl_disabled', None)
            connection = mysql.connector.connect(**DB_CONFIG_FALLBACK)
            return connection
        except mysql.connector.Error as e2:
            current_app.logger.error(f"Error en fallback de conexión MySQL: {e2}")
            return None

def _buscar_fecha_nacimiento(telefono):
    """Busca la fecha de nacimiento de un lead en la base de datos por teléfono."""
    if not telefono:
        return None
        
    conn = _get_db_connection()
    if not conn:
        current_app.logger.warning("No se pudo conectar a la base de datos para buscar fecha de nacimiento")
        return None
    
    try:
        cursor = conn.cursor()
        telefono_norm = _norm_phone(telefono)
        
        # Buscar por teléfono normalizado
        query = "SELECT fecha_nacimiento FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 1"
        cursor.execute(query, (telefono_norm,))
        result = cursor.fetchone()
        
        if result and result[0]:
            fecha_nacimiento = result[0]
            # Convertir a formato YYYY-MM-DD si es necesario
            if isinstance(fecha_nacimiento, str):
                return fecha_nacimiento
            else:
                return fecha_nacimiento.strftime('%Y-%m-%d')
        
        current_app.logger.info(f"No se encontró fecha de nacimiento para el teléfono: {telefono_norm}")
        return None
        
    except mysql.connector.Error as e:
        current_app.logger.error(f"Error al buscar fecha de nacimiento: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def parse_date(date_string):
    """Intenta convertir un string de fecha a objeto date, probando varios formatos."""
    if not isinstance(date_string, str):
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_string, fmt).date()
        except (ValueError, TypeError):
            pass
    current_app.logger.warning(f"No se pudo procesar la fecha: {date_string} con los formatos conocidos.")
    return None

def _extract_availabilities(resp: dict) -> list:
    """Devuelve la lista de availabilities sin importar la profundidad."""
    if not isinstance(resp, dict):
        return []
    if 'availabilities' in resp and isinstance(resp['availabilities'], list):
        return resp['availabilities']
    for key, value in resp.items():
        if isinstance(value, dict):
            found = _extract_availabilities(value)
            if found:
                return found
    return []

# --- Configuración de Caché ---
import tempfile

# Usar tempfile.gettempdir() que es compatible con Windows y Unix
SLOTS_CACHE_DIR = Path(tempfile.gettempdir()) / "cached_slots"
# Asegurar que el directorio existe
SLOTS_CACHE_DIR.mkdir(exist_ok=True)

# --- Endpoints de la API ---
@tuotempo_api.route('/')
def index():
    """Punto de entrada principal que muestra el estado del servicio."""
    return jsonify({
        'service': 'Tuotempo & Leads API',
        'status': 'online',
        'message': 'Welcome! This is an API service. Please use the specific endpoints to interact.'
    })
@tuotempo_api.route('/api/status')
def status():
    """Endpoint de estado para verificar que la API está viva."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': os.getenv('RAILWAY_SERVICE_NAME', 'Unknown')
    })

@tuotempo_api.route('/api/slots', methods=['GET'])
def obtener_slots():
    env = request.args.get('env', 'PRO').upper()
    
    # Valores predeterminados si las variables de entorno no están disponibles
    api_key = os.getenv(f'TUOTEMPO_API_KEY_{env}')
    api_secret = os.getenv(f'TUOTEMPO_API_SECRET_{env}', 'default_secret')
    instance_id = os.getenv('TUOTEMPO_INSTANCE_ID', 'tt_portal_adeslas')
    
    # Usar valores predeterminados para PRO y PRE si no están en las variables de entorno
    if not api_key:
        if env == 'PRO':
            api_key = "24b98d8d41b970d38362b52bd3505c04"
        else:  # PRE
            api_key = "3a5835be0f540c7591c754a2bf0758bb"
    
    current_app.logger.info(f"Usando API key: {api_key[:5]}... para entorno {env} con instance_id {instance_id}")
        
    tuotempo = Tuotempo(api_key, api_secret, instance_id)
    
    centro_id = request.args.get('centro_id')
    fecha_inicio_str = request.args.get('fecha_inicio')
    phone = request.args.get('phone')
    periodo = request.args.get('periodo')

    if not all([centro_id, fecha_inicio_str, phone]):
        return jsonify({'error': 'Faltan parámetros: centro_id, fecha_inicio, phone'}), 400

    try:
        fecha_base_dt = datetime.strptime(fecha_inicio_str, "%d-%m-%Y")
    except ValueError:
        return jsonify({'error': 'Formato de fecha_inicio inválido, usar DD-MM-YYYY'}), 400

    slots_list = []
    slots_return = {}
    
    for offset_weeks in range(4):
        fecha_consulta_dt = fecha_base_dt + timedelta(days=7 * offset_weeks)
        fecha_consulta_str = fecha_consulta_dt.strftime("%d-%m-%Y")
        
        current_app.logger.info(f"Buscando slots para la semana del {fecha_consulta_str}")
        
        tuotempo_call_params = {'locations_lid': [centro_id], 'start_date': fecha_consulta_str, 'days': 7}
        current_app.logger.info(f"[TUOTEMPO_TRACE] Calling get_available_slots with params: {json.dumps(tuotempo_call_params)}")
        
        res = tuotempo.get_available_slots(locations_lid=[centro_id], start_date=fecha_consulta_str, days=7)
        
        current_app.logger.info(f"[TUOTEMPO_TRACE] Raw response from get_available_slots: {json.dumps(res, indent=2)}")
        
        slots_return = res
        current_slots = _extract_availabilities(res)
        
        if current_slots:
            if periodo == 'manana':
                slots_list.extend([s for s in current_slots if int(s['startTime'].split(':')[0]) < 14])
            elif periodo == 'tarde':
                slots_list.extend([s for s in current_slots if int(s['startTime'].split(':')[0]) >= 14])
            else:
                slots_list.extend(current_slots)

        if slots_list:
            current_app.logger.info(f"Encontrados {len(slots_list)} slots. Terminando búsqueda.")
            break

    phone_norm = _norm_phone(phone)
    cache_file = SLOTS_CACHE_DIR / f"slots_{phone_norm}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(slots_return, f, ensure_ascii=False, indent=4)
        current_app.logger.info(f"Slots guardados en caché para el teléfono {phone_norm} en {cache_file}")
    except Exception as e:
        current_app.logger.error(f"No se pudo escribir en el fichero de caché {cache_file}: {e}")

    return jsonify({'success': True, 'slots': slots_list})


@tuotempo_api.route('/api/reservar', methods=['POST'])
def reservar():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    env = data.get('env', 'PRO').upper()
    user_info = data.get('user_info')
    availability = data.get('availability')
    phone_cache = user_info.get('phone') or (user_info.get('phone') if isinstance(user_info, dict) else None)

    if not all([user_info, availability, phone_cache]):
        return jsonify({"error": "Faltan campos clave: user_info, availability o phone"}), 400

    # Valores predeterminados si las variables de entorno no están disponibles
    api_key = os.getenv(f'TUOTEMPO_API_KEY_{env}')
    api_secret = os.getenv(f'TUOTEMPO_API_SECRET_{env}', 'default_secret')
    instance_id = os.getenv('TUOTEMPO_INSTANCE_ID', 'tt_portal_adeslas')
    
    # Usar valores predeterminados para PRO y PRE si no están en las variables de entorno
    if not api_key:
        if env == 'PRO':
            api_key = "24b98d8d41b970d38362b52bd3505c04"
        else:  # PRE
            api_key = "3a5835be0f540c7591c754a2bf0758bb"
    
    current_app.logger.info(f"Usando API key: {api_key[:5]}... para entorno {env} con instance_id {instance_id}")

    tuotempo = Tuotempo(api_key, api_secret, instance_id)

    if isinstance(availability, dict):
        # Normalizar claves de disponibilidad a formato esperado por Tuotempo (snakecase minúsculas)
        if 'activity_id' in availability:
            availability['activityid'] = availability.pop('activity_id')
        if 'resource_id' in availability:
            availability['resourceid'] = availability.pop('resource_id')
        # También convertir camelCase de la API original
        if 'activityId' in availability:
            availability['activityid'] = availability.pop('activityId')
        if 'resourceId' in availability:
            availability['resourceid'] = availability.pop('resourceId')
            
        # Si activityid está vacío, usar el valor por defecto
        if 'activityid' not in availability or not availability['activityid']:
            default_activity_id = os.getenv('TUOTEMPO_ACTIVITY_ID', 'sc159232371eb9c1')
            current_app.logger.info(f"activityId vacío o no presente. Usando valor por defecto: {default_activity_id}")
            availability['activityid'] = default_activity_id

    critical_keys = {'endTime', 'resourceid', 'activityid'}
    if critical_keys - availability.keys():
        cache_path = SLOTS_CACHE_DIR / f"slots_{_norm_phone(phone_cache)}.json"
        if cache_path.exists():
            current_app.logger.info(f"Fichero de caché encontrado en: {cache_path}")
            try:
                with cache_path.open('r', encoding='utf-8') as f:
                    cached_response = json.load(f)
                slots_list = _extract_availabilities(cached_response)
                
                availability_completed = False
                for s in slots_list:
                    if not isinstance(s, dict): continue
                    
                    cached_date = parse_date(s.get('start_date'))
                    request_date = parse_date(availability.get('start_date'))

                    # Log detallado para depurar la comparación
                    current_app.logger.info(f"[CACHE_DEBUG] Comparing cache slot: [date: {s.get('start_date')}, time: {s.get('startTime')}] with request: [date: {availability.get('start_date')}, time: {availability.get('startTime')}]")

                    if cached_date and request_date and cached_date == request_date and s.get('startTime') == availability.get('startTime'):
                        # Trazas adicionales para verificar IDs
                        found_resource_id = s.get('resourceid')
                        found_activity_id = s.get('activityid')
                        current_app.logger.info(f"Slot coincidente encontrado en caché. resourceId: '{found_resource_id}', activityId: '{found_activity_id}'")
                        
                        current_app.logger.info(f"Completando datos desde el slot de caché: {s}")
                        availability.update(s)
                        availability_completed = True
                        current_app.logger.info(f"Availability completada desde cache. Datos actuales: {availability}")
                        break                 
                if not availability_completed:
                    current_app.logger.warning(f"No se encontró un slot coincidente en la caché para {availability.get('start_date')} a las {availability.get('startTime')}")
            except Exception as e:
                current_app.logger.error(f"Error al leer o procesar el fichero de caché {cache_path}: {e}")
        else:
            current_app.logger.warning(f"Fichero de caché NO encontrado en la ruta: {cache_path}")

    missing_fields = [k for k in critical_keys if k not in availability or not availability[k]]
    if missing_fields:
        return jsonify({"error": f"Faltan campos críticos para la reserva: {missing_fields}. No se pudieron completar desde la caché."}), 400

    # Buscar fecha de nacimiento en BD si no viene en el request
    birthday = user_info.get('birthday')
    if not birthday:
        current_app.logger.info(f"Fecha de nacimiento no proporcionada. Buscando en BD para teléfono: {user_info.get('phone')}")
        birthday = _buscar_fecha_nacimiento(user_info.get('phone'))
        if birthday:
            current_app.logger.info(f"Fecha de nacimiento encontrada en BD: {birthday}")
        else:
            current_app.logger.warning(f"No se encontró fecha de nacimiento en BD para teléfono: {user_info.get('phone')}")
            # Asignar fecha por defecto si no se encuentra
            birthday = '1920-01-01'
            current_app.logger.info(f"Asignando fecha de nacimiento por defecto: {birthday}")

    user_info_norm = {
        'name': user_info.get('fname'),
        'surname': user_info.get('lname'),
        'birth_date': birthday,
        'mobile_phone': user_info.get('phone')
    }
    
    availability_norm = {
        'start_date': availability.get('start_date'),
        'startTime': availability.get('startTime'),
        'endTime': availability.get('endTime'),
        'resourceid': availability.get('resourceid'),
        'activityid': availability.get('activityid')
    }

    try:
        tuotempo_call_params = {'user_info': user_info_norm, 'availability': availability_norm}
        current_app.logger.info(f"[TUOTEMPO_TRACE] Calling create_reservation with params: {json.dumps(tuotempo_call_params)}")

        res = tuotempo.create_reservation(user_info=user_info_norm, availability=availability_norm)

        current_app.logger.info(f"[TUOTEMPO_TRACE] Raw response from create_reservation: {json.dumps(res)}")

        if res.get('result') == 'OK':
            return jsonify(res), 200
        else:
            current_app.logger.error(f"Fallo en la reserva de Tuotempo: {res}")
            return jsonify({"error": "No se pudo confirmar la cita", "details": res}), 502
    except Exception as e:
        current_app.logger.exception("Excepción al llamar a Tuotempo para crear la reserva")
        return jsonify({"error": "Ocurrió un error interno en el servidor"}), 500



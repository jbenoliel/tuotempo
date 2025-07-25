from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import json
import re
import logging
# Temporalmente comentado para resolver importación circular
# from tuotempo import Tuotempo

# Crear el Blueprint para la API de Tuotempo
tuotempo_api = Blueprint('tuotempo_api', __name__)

# --- Funciones de Utilidad ---
def _norm_phone(phone: str) -> str:
    """Normaliza un número de teléfono eliminando caracteres no numéricos."""
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)

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
        res = tuotempo.get_available_slots(locations_lid=[centro_id], start_date=fecha_consulta_str, days=7)
        current_app.logger.info(f"Respuesta CRUDA de Tuotempo API: {json.dumps(res, indent=2)}")
        
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
            try:
                with cache_path.open('r', encoding='utf-8') as f:
                    cached_response = json.load(f)
                slots_list = _extract_availabilities(cached_response)
                
                availability_completed = False
                for s in slots_list:
                    if not isinstance(s, dict): continue
                    
                    cached_date = parse_date(s.get('start_date'))
                    request_date = parse_date(availability.get('start_date'))

                    if cached_date and request_date and cached_date == request_date and s.get('startTime') == availability.get('startTime'):
                        current_app.logger.info(f"Slot encontrado en caché. Completando datos desde: {s}")
                        availability.update(s)
                        availability_completed = True
                        current_app.logger.info(f"Availability completada desde cache. Datos actuales: {availability}")
                        break                 
                if not availability_completed:
                    current_app.logger.warning(f"No se encontró un slot coincidente en la caché para {availability.get('start_date')} a las {availability.get('startTime')}")
            except Exception as e:
                current_app.logger.error(f"Error al leer o procesar el fichero de caché {cache_path}: {e}")

    missing_fields = [k for k in critical_keys if k not in availability or not availability[k]]
    if missing_fields:
        return jsonify({"error": f"Faltan campos críticos para la reserva: {missing_fields}. No se pudieron completar desde la caché."}), 400

    user_info_norm = {
        'name': user_info.get('fname'),
        'surname': user_info.get('lname'),
        'birth_date': user_info.get('birthday'),
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
        res = tuotempo.create_reservation(user_info=user_info_norm, availability=availability_norm)
        if res.get('result') == 'OK':
            return jsonify(res), 200
        else:
            current_app.logger.error(f"Fallo en la reserva de Tuotempo: {res}")
            return jsonify({"error": "No se pudo confirmar la cita", "details": res}), 502
    except Exception as e:
        current_app.logger.exception("Excepción al llamar a Tuotempo para crear la reserva")
        return jsonify({"error": "Ocurrió un error interno en el servidor"}), 500



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

def _normalize_time_str(time_str):
    """Normaliza un string de hora a formato HH:MM, eliminando segundos si existen."""
    if not isinstance(time_str, str):
        return None
    parts = time_str.split(':')
    if len(parts) >= 2:
        return f"{parts[0]}:{parts[1]}"
    return None

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


@tuotempo_api.route('/api/logs/tuotempo', methods=['GET'])
def get_tuotempo_logs():
    """Endpoint para obtener los logs de las APIs de tuotempo."""
    try:
        from railway_logs_helper import read_tuotempo_logs, filter_logs_by_time

        # Parámetros opcionales
        max_lines = int(request.args.get('max_lines', 50))
        hours_ago = int(request.args.get('hours_ago', 24))

        # Leer logs
        logs = read_tuotempo_logs(max_lines)

        # Filtrar por tiempo si se especifica
        if hours_ago > 0:
            logs = filter_logs_by_time(logs, hours_ago)

        return jsonify({
            'success': True,
            'total_logs': len(logs),
            'logs': logs,
            'parameters': {
                'max_lines': max_lines,
                'hours_ago': hours_ago
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error al obtener logs de tuotempo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tuotempo_api.route('/api/debug/cache', methods=['GET'])
def debug_cache():
    """Endpoint para diagnosticar problemas con el caché de slots."""
    try:
        phone = request.args.get('phone', '+34629203315')

        # Normalizar teléfono usando la función estándar
        phone_cache = _norm_phone(phone)

        result = {
            "phone_original": phone,
            "phone_normalized": phone_cache,
            "cache_info": {}
        }

        # Verificar archivo de caché
        cache_path = Path("/tmp/cached_slots") / f"slots_{phone_cache}.json"
        result["cache_file_path"] = str(cache_path)
        result["cache_file_exists"] = cache_path.exists()

        if cache_path.exists():
            try:
                with cache_path.open('r', encoding='utf-8') as f:
                    cached_data = json.load(f)

                # Estadísticas del archivo de caché
                if 'availabilities' in cached_data:
                    availabilities = cached_data['availabilities']
                    result["cache_info"] = {
                        "total_slots": len(availabilities),
                        "file_size_bytes": cache_path.stat().st_size,
                        "last_modified": datetime.fromtimestamp(cache_path.stat().st_mtime).isoformat()
                    }

                    # Mostrar algunos slots de ejemplo
                    sample_slots = []
                    for slot in availabilities[:5]:  # Primeros 5 slots
                        if isinstance(slot, dict):
                            sample_slots.append({
                                "start_date": slot.get('start_date'),
                                "startTime": slot.get('startTime'),
                                "endTime": slot.get('endTime'),
                                "resourceid": slot.get('resourceid'),
                                "activityid": slot.get('activityid'),
                                "areaTitle": slot.get('areaTitle')
                            })
                    result["cache_info"]["sample_slots"] = sample_slots

                    # Buscar el slot específico que está causando problema
                    target_date = "10/10/2025"  # Fecha del problema
                    target_time = "13:30"      # Hora del problema

                    matching_slots = []
                    for slot in availabilities:
                        if isinstance(slot, dict):
                            if (slot.get('start_date') == target_date and
                                slot.get('startTime') == target_time):
                                matching_slots.append({
                                    "start_date": slot.get('start_date'),
                                    "startTime": slot.get('startTime'),
                                    "endTime": slot.get('endTime'),
                                    "resourceid": slot.get('resourceid'),
                                    "activityid": slot.get('activityid'),
                                    "areaTitle": slot.get('areaTitle')
                                })

                    result["cache_info"]["target_slot_found"] = len(matching_slots) > 0
                    result["cache_info"]["matching_slots"] = matching_slots

                else:
                    result["cache_info"]["error"] = "No 'availabilities' key in cache file"

            except Exception as e:
                result["cache_info"]["error"] = f"Error reading cache file: {str(e)}"
        else:
            result["cache_info"]["error"] = "Cache file does not exist"

            # Listar archivos en el directorio de caché
            cache_dir = Path("/tmp/cached_slots")
            if cache_dir.exists():
                cache_files = [f.name for f in cache_dir.iterdir() if f.is_file()]
                result["available_cache_files"] = cache_files
            else:
                result["cache_directory_exists"] = False

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error en debug_cache: {e}")
        return jsonify({
            "error": f"Error debugging cache: {str(e)}"
        }), 500

@tuotempo_api.route('/api/reservar', methods=['POST'])
def reservar():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    # Generar clave de idempotencia para evitar reservas duplicadas
    user_info = data.get('user_info', {})
    availability = data.get('availability', {})

    # Normalizar teléfono INMEDIATAMENTE para usar en clave de idempotencia
    phone_raw = user_info.get('phone') or (user_info.get('phone') if isinstance(user_info, dict) else None)
    if not phone_raw:
        return jsonify({"error": "Falta el teléfono en user_info"}), 400

    phone_cache = _norm_phone(phone_raw)

    # Crear clave única basada en teléfono + slot + fecha
    start_date = availability.get('start_date', '')
    start_time = availability.get('startTime', '')
    resource_id = availability.get('resourceid', '')

    idempotency_key = f"{phone_cache}_{start_date}_{start_time}_{resource_id}"
    current_app.logger.info(f"Clave de idempotencia generada: {idempotency_key}")

    # Verificar si ya existe una reserva reciente para esta combinación
    # (implementación simplificada - en producción usar Redis o BD)
    import hashlib
    import time
    cache_key = hashlib.md5(idempotency_key.encode()).hexdigest()
    cache_file = Path(f"/tmp/reservation_cache_{cache_key}.json")

    # Verificar caché de reservas recientes (últimos 2 minutos)
    if cache_file.exists():
        try:
            import json
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)

            cache_time = cached_data.get('timestamp', 0)
            if time.time() - cache_time < 120:  # 2 minutos
                cached_result = cached_data.get('result')
                current_app.logger.info(f"Reserva duplicada detectada - devolviendo resultado cacheado: {cached_result.get('result')}")

                # Si la reserva anterior fue exitosa, devolver el mismo resultado
                if cached_result.get('result') == 'OK':
                    return jsonify(cached_result), 200
                elif cached_result.get('result') == 'SLOT_CONFLICT':
                    return jsonify({
                        "error": cached_result.get('msg', 'Slot no disponible'),
                        "error_type": "SLOT_CONFLICT",
                        "recommended_action": cached_result.get('recommended_action'),
                        "details": cached_result.get('details', {})
                    }), 409
        except Exception as e:
            current_app.logger.warning(f"Error leyendo caché de idempotencia: {e}")
            # Continuar con la reserva normal si hay error en caché

    env = data.get('env', 'PRO').upper()

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
        # El teléfono ya está normalizado arriba
        cache_path = SLOTS_CACHE_DIR / f"slots_{phone_cache}.json"
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

                    # Normalizar horas para una comparación robusta (ignorar segundos)
                    cached_time_norm = _normalize_time_str(s.get('startTime'))
                    request_time_norm = _normalize_time_str(availability.get('startTime'))

                    # Log detallado para depurar la comparación
                    current_app.logger.info(f"[CACHE_DEBUG] Comparing cache slot: [date: {s.get('start_date')} -> {cached_date}, time: {cached_time_norm}] with request: [date: {availability.get('start_date')} -> {request_date}, time: {request_time_norm}]")
                    current_app.logger.info(f"[CACHE_DEBUG] Date match: {cached_date == request_date}, Time match: {cached_time_norm == request_time_norm}")

                    if cached_date and request_date and cached_date == request_date and cached_time_norm and cached_time_norm == request_time_norm:
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
        # Si falta resourceid, intentar obtener slots frescos
        if 'resourceid' in missing_fields:
            current_app.logger.warning(f"Falta resourceid, intentando obtener slots para completar datos...")

            # Buscar slots disponibles para esa fecha/hora
            try:
                # Usar teléfono ya normalizado
                phone_for_slots = phone_cache

                # Obtener slots para esa fecha
                from tuotempo import Tuotempo
                tuotempo_instance = Tuotempo(
                    api_key=os.getenv('TUOTEMPO_API_KEY'),
                    secret_key=os.getenv('TUOTEMPO_SECRET_KEY'),
                    instance_id=os.getenv('TUOTEMPO_INSTANCE_ID')
                )

                # Formato de fecha esperado por get_available_slots
                date_parts = availability.get('start_date', '').split('-')
                if len(date_parts) == 3:
                    formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"  # DD-MM-YYYY
                else:
                    formatted_date = availability.get('start_date', '')

                current_app.logger.info(f"Buscando slots para fecha: {formatted_date}")
                slots_response = tuotempo_instance.get_available_slots(
                    locations_lid=["44kowswy"], # ID por defecto, ajustar según necesidad
                    start_date=formatted_date,
                    days=1
                )

                if slots_response and 'availabilities' in slots_response:
                    slots_list = slots_response['availabilities']
                    request_time_norm = _normalize_time_str(availability.get('startTime'))

                    # Buscar el slot exacto
                    for slot in slots_list:
                        slot_time_norm = _normalize_time_str(slot.get('startTime'))
                        if slot_time_norm == request_time_norm:
                            current_app.logger.info(f"Slot encontrado en tiempo real: {slot.get('resourceid')}")
                            availability.update(slot)
                            missing_fields = [k for k in critical_keys if k not in availability or not availability[k]]
                            break

                    if missing_fields:
                        current_app.logger.warning(f"No se encontró slot exacto para {availability.get('startTime')} en los {len(slots_list)} slots disponibles")

            except Exception as e:
                current_app.logger.error(f"Error al obtener slots en tiempo real: {e}")

        # Verificar nuevamente si aún faltan campos después del intento de completar
        missing_fields = [k for k in critical_keys if k not in availability or not availability[k]]
        if missing_fields:
            return jsonify({
                "error": f"Faltan campos críticos para la reserva: {missing_fields}. No se pudieron completar desde la caché ni en tiempo real.",
                "suggestion": "Por favor, obtén primero los slots disponibles usando /api/slots y luego usa los datos completos para la reserva."
            }), 400

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

        # Guardar resultado en caché para idempotencia
        try:
            import time
            cache_data = {
                'timestamp': time.time(),
                'idempotency_key': idempotency_key,
                'result': res
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            current_app.logger.info(f"Resultado guardado en caché para clave: {idempotency_key}")
        except Exception as e:
            current_app.logger.warning(f"Error guardando caché de idempotencia: {e}")

        if res.get('result') == 'OK':
            return jsonify(res), 200
        elif res.get('result') == 'SLOT_CONFLICT':
            # Error de conflicto de slot - devolver 409 Conflict en lugar de 502
            current_app.logger.warning(f"Conflicto de slot en reserva: {res.get('msg')}")
            return jsonify({
                "error": res.get('msg', 'Slot no disponible'),
                "error_type": "SLOT_CONFLICT",
                "recommended_action": res.get('recommended_action'),
                "details": res.get('details', {})
            }), 409
        elif res.get('result') == 'MAX_RESERVATIONS':
            # Error de máximo de reservas - devolver 429 Too Many Requests
            current_app.logger.warning(f"Máximo de reservas alcanzado: {res.get('msg')}")
            return jsonify({
                "error": res.get('msg', 'Máximo de reservas alcanzado'),
                "error_type": "MAX_RESERVATIONS",
                "recommended_action": res.get('recommended_action'),
                "details": res.get('details', {})
            }), 429
        else:
            current_app.logger.error(f"Fallo en la reserva de Tuotempo: {res}")
            return jsonify({
                "error": "No se pudo confirmar la cita",
                "error_type": res.get('error_type', 'UNKNOWN'),
                "details": res
            }), 502
    except Exception as e:
        current_app.logger.exception("Excepción al llamar a Tuotempo para crear la reserva")
        return jsonify({"error": "Ocurrió un error interno en el servidor"}), 500



from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import logging
import json
import re
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
from tuotempo_api import TuoTempoAPI
from flask_bcrypt import Bcrypt

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Utilidad para normalizar teléfonos (quitar +, espacios y cualquier cosa que no sea dígito)

def _norm_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return phone
    return re.sub(r"\D", "", phone)

# Carpeta para cachear slots
SLOTS_CACHE_DIR = Path("cached_slots")
SLOTS_CACHE_DIR.mkdir(exist_ok=True)

# Crear la aplicación Flask
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.bcrypt = bcrypt

# Configurar CORS
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "*")
allowed_origins = [o.strip() for o in frontend_origin_env.split(',')]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv('SECRET_KEY', 'clave-secreta-por-defecto')

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        "service": "API TuoTempo Unificada",
        "status": "online",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/slots', methods=['GET'])
def obtener_slots():
    env = request.args.get('env')
    centro_id = request.args.get('centro_id')
    actividad_id = request.args.get('actividad_id', 'sc159232371eb9c1')
    fecha_inicio = request.args.get('fecha_inicio')
    resource_id = request.args.get('resource_id')
    time_preference = request.args.get('time_preference')  # MORNING o AFTERNOON
    phone = request.args.get('phone')

    if not all([env, centro_id, fecha_inicio, phone]):
        return jsonify({"success": False, "message": "Faltan parámetros requeridos (env, centro_id, actividad_id, fecha_inicio, phone)"}), 400

    if env.upper() == 'PRE':
        api_key = os.getenv('TUOTEMPO_API_KEY_PRE')
        api_secret = os.getenv('TUOTEMPO_API_SECRET_PRE')
    elif env.upper() == 'PRO':
        api_key = os.getenv('TUOTEMPO_API_KEY_PRO')
        api_secret = os.getenv('TUOTEMPO_API_SECRET_PRO')
    else:
        return jsonify({"success": False, "message": "Entorno no válido. Usa 'PRE' o 'PRO'."}), 400

    instance_id = os.getenv('TUOTEMPO_INSTANCE_ID')
    tuotempo = TuoTempoAPI(api_key, api_secret, instance_id, env)

    # Convertir fecha a guiones si viene con /
    if fecha_inicio and '/' in fecha_inicio:
        fecha_inicio = fecha_inicio.replace('/', '-')

    try:
        # --- Búsqueda progresiva: fecha_inicio, +7 días y +14 días ---
        if not fecha_inicio:
            raise ValueError("fecha_inicio es requerida")

        fecha_base_dt = datetime.strptime(fecha_inicio, "%d-%m-%Y")
        slots_list = []
        slots_return = {}

        for offset_weeks in range(3):  # 0, 7, 14 días
            consulta_dt = fecha_base_dt + timedelta(days=7 * offset_weeks)
            consulta_str = consulta_dt.strftime("%d-%m-%Y")
            logging.info(f"Intento {offset_weeks + 1}/3 - Buscando slots para {consulta_str}")

            res = tuotempo.get_available_slots(
                activity_id=actividad_id,
                area_id=centro_id,
                start_date=consulta_str,
                resource_id=resource_id,
                time_preference=time_preference
            )
            slots_return = res  # guardamos la última respuesta, tenga o no slots

            if isinstance(res, dict):
                result_flag = res.get('result')
                exception_code = res.get('exception')

                if result_flag == 'OK':
                    slots_list = res.get('availabilities', [])
                elif result_flag == 'EXCEPTION' and exception_code == 'MEMBER_NOT_FOUND':
                    slots_list = []  # sin disponibilidad, seguimos buscando
                else:
                    error_message = res.get('msg', 'Error desconocido')
                    logging.error(f"Error al obtener slots de Tuotempo: {error_message}")
                    return jsonify({'success': False, 'message': f'Error al obtener slots: {error_message}'}), 500

            if slots_list:
                break  # encontramos disponibilidad, salimos del bucle

        # Guardar la respuesta (del intento con más información) en caché
        cache_dir = Path('cached_slots')
        cache_dir.mkdir(exist_ok=True)
        phone_norm = _norm_phone(phone)
        cache_file = cache_dir / f"slots_{phone_norm}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(slots_return, f, ensure_ascii=False, indent=4)
        logging.info(f"Slots guardados en caché para el teléfono {phone_norm} en {cache_file}")

        return jsonify({'success': True, 'slots': slots_list})

        # Si la respuesta no es un dict, es un error inesperado
        logging.error(f"Respuesta inesperada de Tuotempo: {slots_return}")
        return jsonify({'success': False, 'message': 'Respuesta inesperada de Tuotempo'}), 500

    except Exception as e:
        logging.error(f"Excepción en /api/slots: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@app.route('/api/reservar', methods=['POST'])
def reservar():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    env = data.get('env', 'PRO').upper()
    user_info = data.get('user_info')
    availability = data.get('availability')
    phone_cache = data.get('phone') or (user_info.get('phone') if isinstance(user_info, dict) else None)
    desired_date = data.get('start_date')
    desired_time = data.get('startTime')
    cancel_after = bool(data.get('cancel'))

    # --- Normalización de campos para robustez ---
    if isinstance(availability, dict):
        # Si el payload viene con los nombres de campo antiguos (con guion bajo), los renombramos.
        if 'activity_id' in availability:
            availability['activityid'] = availability.pop('activity_id')
        if 'resource_id' in availability:
            availability['resourceid'] = availability.pop('resource_id')

    # --- Completar availability desde la caché si faltan campos críticos ---
    critical_keys = {'endTime', 'resourceid', 'activityid'}
    if availability and phone_cache and (critical_keys - availability.keys()):
        cache_path = SLOTS_CACHE_DIR / f"slots_{phone_cache}.json"
        if cache_path.exists():
            try:
                with cache_path.open('r', encoding='utf-8') as f:
                    cached_response = json.load(f)
                slots_list = cached_response.get('availabilities', [])
                # usar fecha/hora del availability parcial
                partial_date = availability.get('start_date')
                partial_time = availability.get('startTime')
                def norm(d):
                    try:
                        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y") if '-' in d else d
                    except Exception:
                        return d
                norm_partial_date = norm(partial_date) if partial_date else None
                for s in slots_list:
                    if not isinstance(s, dict):
                        continue
                    if (s.get('start_date') in {partial_date, norm_partial_date}) and s.get('startTime') == partial_time:
                        # merge missing keys
                        for k in critical_keys:
                            if k not in availability and k in s:
                                availability[k] = s[k]
                        logger.info(f"Availability completada desde cache: añadidos {[k for k in critical_keys if k in s]}")
                        break
            except Exception as e:
                logger.warning(f"No se pudo completar availability desde cache: {e}")

    # Si no se envió availability pero hay phone, intentamos cargar del cache
    if availability is None and phone_cache:
        cache_path = SLOTS_CACHE_DIR / f"slots_{phone_cache}.json"
        if cache_path.exists():
            logger.info(f"Cache file found: {cache_path}")
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    cached_response = json.load(f)
                logger.info(f"Cache content loaded. Keys: {list(cached_response.keys())}")

                slots_list = cached_response.get('availabilities', [])
                if slots_list:
                    logger.info(f"Se extrajeron {len(slots_list)} slots de la clave 'availabilities' en el caché.")
                else:
                    logger.warning("No se encontró la clave 'availabilities' o estaba vacía en el caché.")

                # Si hay slots en el cache, buscar el que coincida
                if slots_list and desired_date and desired_time:
                    def normalize(d):
                        try:
                            return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y") if '-' in d else d
                        except ValueError:
                            return d
                    norm_date = normalize(desired_date)
                    for i, s in enumerate(slots_list):
                        logger.info(f"Processing slot item #{i}: Type={type(s)}, Content={s}")
                        # Ignorar elementos que no son diccionarios (slots válidos)
                        if not isinstance(s, dict):
                            logger.warning(f"Item #{i} is not a dict, skipping.")
                            continue
                        if s.get('start_date') == norm_date and s.get('startTime') == desired_time:
                            availability = s
                            logger.info(f"SUCCESS: Slot found in cache for {norm_date} at {desired_time}")
                            break
                if not availability:
                    logger.warning("Slot NOT found in cache for the specified date/time.")
                
                # Borrar el cache DESPUÉS de usarlo con éxito
                if availability:
                    cache_path.unlink(missing_ok=True)
                    logger.info(f"Cache {cache_path} eliminado tras su uso.")

            except Exception as e:
                logger.warning(f"No se pudo leer o procesar el cache de slots: {e}")

    if not user_info or not availability:
        return jsonify({"error": "Faltan 'user_info' o 'availability' en el payload"}), 400

    required_keys = ['fname', 'lname', 'birthday', 'phone']
    if not all(key in user_info for key in required_keys):
        return jsonify({"error": f"Faltan datos en user_info. Se requiere: {required_keys}"}), 400

    try:
        api_client = TuoTempoAPI(environment=env)
        # Extraer solo los campos requeridos por la función para evitar TypeErrors
        required_user_fields = {
            'fname': user_info.get('fname'),
            'lname': user_info.get('lname'),
            'birthday': user_info.get('birthday'),
            'phone': user_info.get('phone')
        }
        user_reg_response = api_client.register_non_insured_user(**required_user_fields)

        if not api_client.session_id:
            return jsonify({"error": "No se pudo registrar el usuario", "details": user_reg_response}), 502

        confirm_response = api_client.confirm_appointment(availability, user_info['phone'])

        if confirm_response.get("result") != "OK":
            return jsonify({"error": "No se pudo confirmar la cita", "details": confirm_response}), 502

        if cancel_after:
            resid = confirm_response.get("return") or confirm_response.get("resid")
            if resid:
                cancel_resp = api_client.cancel_appointment(resid, "Cancelación automática")
                return jsonify({"booking": confirm_response, "cancellation": cancel_resp})

        return jsonify(confirm_response)

    except Exception as e:
        logger.error(f"Excepción inesperada durante la reserva: {e}")
        return jsonify({"error": "Ocurrió un error inesperado"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

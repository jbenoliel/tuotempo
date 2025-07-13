from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import logging
import json
from pathlib import Path
from datetime import datetime
from tuotempo_api import TuoTempoAPI
from flask_bcrypt import Bcrypt

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    try:
        centro_id = request.args.get('centro_id')
        actividad_id = request.args.get('actividad_id')
        fecha_inicio = request.args.get('fecha_inicio')
        recurso_id = request.args.get('recurso_id')
        phone_cache = request.args.get('phone')

        if not all([centro_id, actividad_id, fecha_inicio]):
            return jsonify({"success": False, "message": "centro_id, actividad_id y fecha_inicio son obligatorios"}), 400

        api = TuoTempoAPI(lang='es', environment='PRE')
        slots_response = api.get_available_slots(
            activity_id=actividad_id,
            area_id=centro_id,
            start_date=fecha_inicio,
            resource_id=recurso_id
        )



        if slots_response.get("result") != "OK":
            return jsonify({"success": False, "message": f"Error al obtener slots: {slots_response.get('message', 'Error desconocido')}"}), 500

        # Guardar en cache si se proporcionó phone
        if phone_cache and slots_response:
            cache_path = SLOTS_CACHE_DIR / f"slots_{phone_cache}.json"
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump(slots_response, f, indent=4)
                logger.info(f"Slots guardados en cache: {cache_path}")
            except Exception as e:
                logger.warning(f"No se pudo guardar el cache de slots: {e}")

        # Extraer la lista de slots para la respuesta
        slots_return = slots_response.get('return')
        slots_list = []
        if isinstance(slots_return, list):
            slots_list = slots_return
        elif isinstance(slots_return, dict):
            slots_list = slots_return.get('availabilities', [])

        return jsonify({
            "success": True,
            "message": f"Se encontraron {len(slots_list)} slots disponibles",
            "slots": slots_list
        })

    except Exception as e:
        logger.exception(f"Error al procesar la solicitud de slots: {e}")
        return jsonify({"success": False, "message": f"Error al procesar la solicitud: {e}"}), 500

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

    # Si no se envió availability pero hay phone, intentamos cargar del cache
    if availability is None and phone_cache:
        cache_path = SLOTS_CACHE_DIR / f"slots_{phone_cache}.json"
        if cache_path.exists():
            logger.info(f"Cache file found: {cache_path}")
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    cached_response = json.load(f)
                logger.info(f"Cache content loaded. Keys: {list(cached_response.keys())}")

                slots_return = cached_response.get('return')
                slots_list = []
                # La verdadera lista de slots está en la clave 'availabilities' del diccionario 'return'
                if isinstance(slots_return, dict) and 'availabilities' in slots_return:
                    slots_list = slots_return.get('availabilities', [])
                    logger.info(f"Extracted {len(slots_list)} slots from 'availabilities' key.")
                else:
                    logger.warning(f"Could not find 'availabilities' key in the cached response.")

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

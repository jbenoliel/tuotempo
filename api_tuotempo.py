from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import logging
import json
import time
from datetime import datetime
from tuotempo_api import TuoTempoAPI
from flask_bcrypt import Bcrypt

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Crear la aplicación Flask
app = Flask(__name__)

bcrypt = Bcrypt(app)
app.bcrypt = bcrypt # Adjuntar bcrypt a la app para que esté disponible en current_app

# Configurar CORS para permitir peticiones ÚNICAMENTE desde el dashboard de producción
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "*")
# Permitir lista separada por comas
allowed_origins = [o.strip() for o in frontend_origin_env.split(',')]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# Configuración de la aplicación
app.config['JSON_AS_ASCII'] = False  # Para manejar caracteres especiales en JSON
app.secret_key = os.getenv('SECRET_KEY', 'clave-secreta-por-defecto')

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint para verificar el estado de la API"""
    return jsonify({
        "service": "API TuoTempo Unificada",
        "status": "online",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# ========== ENDPOINTS PARA CENTROS ==========

@app.route('/api/centros', methods=['GET'])
def obtener_centros():
    """
    Endpoint para obtener centros de TuoTempo
    
    Query parameters:
    - cp: Código postal (opcional)
    - provincia: Provincia (opcional)
    
    Returns:
        JSON con la lista de centros
    """
    try:
        # Obtener parámetros de la solicitud
        codigo_postal = request.args.get('cp')
        provincia = request.args.get('provincia')
        
        logger.info(f"Buscando centros - CP: {codigo_postal}, Provincia: {provincia}")
        
        # Crear instancia de la API
        api = TuoTempoAPI(lang='es', environment='PRE')
        
        # Obtener centros (primero por provincia si se especifica)
        centers_response = api.get_centers(province=provincia)

        if centers_response.get("result") != "OK":
            error_msg = f"Error al obtener centros: {centers_response.get('message', 'Error desconocido')}"
            logger.error(error_msg)
            return jsonify({"success": False, "message": error_msg}), 500

        # Extraer la lista de centros
        centers_list = centers_response.get('return', {}).get('results', [])
        logger.info(f"Se encontraron {len(centers_list)} centros en total antes de filtrar.")

        if not centers_list:
            return jsonify({"success": True, "message": "No se encontraron centros", "centros": []}), 200

        # Filtrar por código postal si se especifica
        if codigo_postal:
            logger.info(f"Filtrando por código postal: '{codigo_postal}'")
            original_count = len(centers_list)
            centers_list = [
                centro for centro in centers_list
                if isinstance(centro, dict) and str(centro.get('cp', '')).strip() == str(codigo_postal).strip()
            ]
            logger.info(f"Filtrado completo. Centros antes: {original_count}, Centros después: {len(centers_list)}")
        
        # Campos a incluir en la respuesta
        campos = [
            'areaid',
            'areaTitle',
            'address',
            'cp',
            'city',
            'province',
            'phone'
        ]
        
        # Formatear la respuesta
        centros_formateados = []
        for centro in centers_list:
            if not isinstance(centro, dict):
                continue
                
            centro_formateado = {campo: centro.get(campo, '') for campo in campos}
            centros_formateados.append(centro_formateado)
        
        # Devolver la respuesta
        return jsonify({
            "success": True,
            "message": f"Se encontraron {len(centros_formateados)} centros",
            "centros": centros_formateados
        })
        
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al procesar la solicitud: {str(e)}"
        }), 500

@app.route('/api/centros/<codigo_postal>', methods=['GET'])
def obtener_centros_por_cp(codigo_postal):
    """
    Endpoint para obtener centros por código postal (versión REST)
    
    Args:
        codigo_postal: Código postal a buscar
    
    Returns:
        JSON con la lista de centros
    """
    # Redirigir a la versión con query parameters
    return obtener_centros()

# ========== ENDPOINTS PARA ACTIVIDADES ==========

@app.route('/api/actividades', methods=['GET'])
def obtener_actividades():
    """
    Endpoint para obtener actividades disponibles en un centro
    
    Query parameters:
    - centro_id: ID del centro (obligatorio)
    
    Returns:
        JSON con la lista de actividades
    """
    try:
        # Obtener parámetros de la solicitud
        centro_id = request.args.get('centro_id')
        
        if not centro_id:
            return jsonify({
                "success": False,
                "message": "El parámetro centro_id es obligatorio"
            }), 400
        
        logger.info(f"Buscando actividades para centro ID: {centro_id}")
        
        # Crear instancia de la API
        api = TuoTempoAPI(lang='es', environment='PRE')
        
        # Obtener actividades
        activities_response = api.get_activities(centro_id)
        
        if activities_response.get("result") != "OK":
            error_msg = f"Error al obtener actividades: {activities_response.get('message', 'Error desconocido')}"
            logger.error(error_msg)
            return jsonify({"success": False, "message": error_msg}), 500
        
        # Extraer la lista de actividades
        activities_list = activities_response.get('return', {}).get('results', [])
        
        if not activities_list:
            return jsonify({"success": True, "message": "No se encontraron actividades", "actividades": []}), 200
        
        # Campos a incluir en la respuesta
        campos = [
            'activityid',
            'activityTitle',
            'description'
        ]
        
        # Formatear la respuesta
        actividades_formateadas = []
        for actividad in activities_list:
            if not isinstance(actividad, dict):
                continue
                
            actividad_formateada = {campo: actividad.get(campo, '') for campo in campos}
            actividades_formateadas.append(actividad_formateada)
        
        # Devolver la respuesta
        return jsonify({
            "success": True,
            "message": f"Se encontraron {len(actividades_formateadas)} actividades",
            "actividades": actividades_formateadas
        })
        
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al procesar la solicitud: {str(e)}"
        }), 500

# ========== ENDPOINTS PARA SLOTS DISPONIBLES ==========

@app.route('/api/slots', methods=['GET'])
def obtener_slots():
    """
    Endpoint para obtener slots disponibles
    
    Query parameters:
    - centro_id: ID del centro (obligatorio)
    - actividad_id: ID de la actividad (obligatorio)
    - fecha_inicio: Fecha de inicio en formato DD/MM/YYYY (obligatorio)
    - recurso_id: ID del recurso/especialista (opcional)
    
    Returns:
        JSON con la lista de slots disponibles
    """
    try:
        # Obtener parámetros de la solicitud
        centro_id = request.args.get('centro_id')
        actividad_id = request.args.get('actividad_id')
        fecha_inicio = request.args.get('fecha_inicio')
        recurso_id = request.args.get('recurso_id')
        
        # Validar parámetros obligatorios
        if not centro_id or not actividad_id or not fecha_inicio:
            return jsonify({
                "success": False,
                "message": "Los parámetros centro_id, actividad_id y fecha_inicio son obligatorios"
            }), 400
        
        logger.info(f"Buscando slots - Centro: {centro_id}, Actividad: {actividad_id}, Fecha: {fecha_inicio}")
        
        # Crear instancia de la API
        api = TuoTempoAPI(lang='es', environment='PRE')
        
        # Obtener slots disponibles
        slots_response = api.get_available_slots(
            activity_id=actividad_id,
            area_id=centro_id,
            start_date=fecha_inicio,
            resource_id=recurso_id
        )
        
        if slots_response.get("result") != "OK":
            error_msg = f"Error al obtener slots: {slots_response.get('message', 'Error desconocido')}"
            logger.error(error_msg)
            return jsonify({"success": False, "message": error_msg}), 500
        
        # Extraer la lista de slots
        slots_list = slots_response.get('return', {}).get('results', [])
        
        if not slots_list:
            return jsonify({"success": True, "message": "No se encontraron slots disponibles", "slots": []}), 200
        
        # Devolver la respuesta
        return jsonify({
            "success": True,
            "message": f"Se encontraron {len(slots_list)} slots disponibles",
            "slots": slots_list
        })
        
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error al procesar la solicitud: {str(e)}"
        }), 500

from datetime import datetime

# ========== ENDPOINTS PARA REALIZAR RESERVAS ==========

@app.route('/api/reservar', methods=['POST'])
def reservar():
    """Endpoint para reservar un slot siguiendo el flujo completo de TuoTempo."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Extraer datos del usuario y de la cita
    user_info = data.get('user_info')
    availability = data.get('availability')

    if not user_info or not availability:
        return jsonify({"error": "Faltan 'user_info' o 'availability' en el payload"}), 400

    # Validar datos del usuario
    required_user_keys = ['fname', 'lname', 'birthday', 'phone']
    if not all(key in user_info for key in required_user_keys):
        return jsonify({"error": f"Faltan datos en user_info. Se requiere: {required_user_keys}"}), 400

    try:
        # 1. Crear una instancia del cliente de la API
        # Se asume entorno de producción (PRO) para las reservas, como en la lógica anterior.
        api_client = TuoTempoAPI(environment="PRO")

        # 2. Registrar al usuario para obtener el session_id (la clase se encarga de guardarlo)
        logging.info(f"Registrando usuario: {user_info['fname']} {user_info['lname']}")
        user_reg_response = api_client.register_non_insured_user(
            fname=user_info['fname'],
            lname=user_info['lname'],
            birthday=user_info['birthday'],
            phone=user_info['phone']
        )

        if user_reg_response.get("result") != "OK":
            logging.error(f"Error al registrar el usuario en TuoTempo: {user_reg_response}")
            return jsonify({"error": "No se pudo registrar el usuario en TuoTempo", "details": user_reg_response}), 502
        
        logging.info("Usuario registrado exitosamente. Procediendo a confirmar la cita.")

        # 3. Confirmar la cita (la clase ya tiene el session_id necesario)
        confirm_response = api_client.confirm_appointment(
            availability=availability,
            communication_phone=user_info['phone']
        )

        if confirm_response.get("result") != "OK":
            logging.error(f"Error al confirmar la cita en TuoTempo: {confirm_response}")
            return jsonify({"error": "No se pudo confirmar la cita en TuoTempo", "details": confirm_response}), 502

        logging.info("Cita confirmada exitosamente.")
        return jsonify(confirm_response)

    except ValueError as ve:
        # Esto se captura si no se obtiene el session_id (lanzado desde confirm_appointment)
        logging.error(f"Error de valor durante la reserva: {ve}")
        return jsonify({"error": str(ve)}), 500
    except Exception as e:
        logging.error(f"Excepción inesperada durante la reserva: {e}")
        return jsonify({"error": "Ocurrió un error inesperado en el servidor"}), 500

# ========== ENDPOINTS DE UTILIDAD ==========

@app.route('/api/saludo', methods=['GET'])
def saludo():
    """Devuelve un saludo según la hora actual (Buenos días <14h, Buenas tardes >=14h)."""
    hora_actual = datetime.now().hour
    mensaje = "Buenos días" if hora_actual < 14 else "Buenas tardes"
    # Usamos json.dumps con ensure_ascii=False para evitar el escape de caracteres unicode
    response_data = {
        "mensaje": mensaje,
        "hora": hora_actual,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return app.response_class(
        response=json.dumps(response_data, ensure_ascii=False),
        status=200,
        mimetype="application/json; charset=utf-8"
    )

if __name__ == '__main__':
    # Obtener puerto del entorno o usar 5000 por defecto
    port = int(os.getenv('PORT', 5000))
    
    # Ejecutar la aplicación
    app.run(host='0.0.0.0', port=port, debug=True)

# --- API ENCAPSULADA DE DISPONIBILIDADES (V1) ---

def _fetch_tuotempo_availabilities_with_retry(params):
    """
    Función auxiliar que llama a la API de Tuotempo con un reintento.
    """
    base_url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities"
    # Primer intento
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()  # Lanza excepción para errores 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.warning(f"Primer intento a la API de Tuotempo falló: {e}. Reintentando en 1 segundo...")
        time.sleep(1)
        # Segundo intento
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            logging.info("Segundo intento a la API de Tuotempo exitoso.")
            return response.json()
        except requests.exceptions.RequestException as e_retry:
            logging.error(f"El segundo intento a la API de Tuotempo también falló: {e_retry}")
            return None  # Devuelve None si ambos intentos fallan

@app.route('/api/v1/availabilities', methods=['GET'])
def get_availabilities_v1():
    """
    Endpoint para obtener disponibilidades de Tuotempo, con lógica de reintento
    y filtrado por preferencia horaria.

    Parámetros de la query string:
    - activityid: ID de la actividad.
    - areaId: ID del área.
    - start_date: Fecha de inicio en formato DD-MM-YYYY.
    - preferencia: 'manana', 'tarde' o 'indiferente' (opcional, por defecto 'indiferente').
    """
    # 1. Obtener parámetros de la petición
    activity_id = request.args.get('activityid')
    area_id = request.args.get('areaId')
    start_date = request.args.get('start_date')
    preferencia = request.args.get('preferencia', 'indiferente').lower()

    if not all([activity_id, area_id, start_date]):
        return jsonify({"error": "Faltan parámetros requeridos (activityid, areaId, start_date)"}), 400

    # 2. Preparar parámetros para la API de Tuotempo
    params = {
        'lang': 'es',
        'activityid': activity_id,
        'areaId': area_id,
        'start_date': start_date,
        'bypass_availabilities_fallback': 'False',
        'numDays': 15
    }

    # Si hay preferencia, pedimos más resultados para poder filtrar
    if preferencia in ['manana', 'tarde']:
        params['maxResults'] = 20
    else:
        params['maxResults'] = 3

    # 3. Llamar a la API con reintento
    data = _fetch_tuotempo_availabilities_with_retry(params)

    if data is None or not data.get('availabilities'):
        return jsonify({"error": "No se pudieron obtener disponibilidades desde Tuotempo tras dos intentos."}), 503

    availabilities = data['availabilities']

    # 4. Filtrar por preferencia si es necesario
    if preferencia in ['manana', 'tarde']:
        filtered_slots = []
        for slot in availabilities:
            try:
                # La hora viene en formato 'HH:MM'
                slot_time = datetime.strptime(slot['time'], '%H:%M').time()
                
                # Definimos mañana como antes de las 15:00
                is_morning = slot_time.hour < 15
                
                if preferencia == 'manana' and is_morning:
                    filtered_slots.append(slot)
                elif preferencia == 'tarde' and not is_morning:
                    filtered_slots.append(slot)
            except (ValueError, KeyError):
                # Ignorar slots con formato de hora incorrecto
                continue
        
        # Devolvemos hasta 3 resultados filtrados
        return jsonify({"availabilities": filtered_slots[:3]})
    else:
        # Si la preferencia es indiferente, devolvemos los resultados tal cual (ya limitados a 3)
        return jsonify({"availabilities": availabilities})

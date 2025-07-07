from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from tuotempo_api import TuoTempoAPI

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Crear la aplicación Flask
app = Flask(__name__)

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
        
        # Construir parámetros para la API de TuoTempo
        api_params = {'province': provincia}
        if codigo_postal:
            # Pasamos el código postal directamente a la API para un filtrado eficiente
            api_params['cp'] = codigo_postal

        # Obtener centros ya filtrados desde la API
        centers_response = api.get_centers(**api_params)

        if centers_response.get("result") != "OK":
            error_msg = f"Error al obtener centros: {centers_response.get('message', 'Error desconocido')}"
            logger.error(error_msg)
            return jsonify({"success": False, "message": error_msg}), 500

        # Extraer la lista de centros
        centers_list = centers_response.get('return', {}).get('results', [])

        if not centers_list:
            return jsonify({"success": True, "message": "No se encontraron centros para los criterios dados", "centros": []}), 200
        
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

if __name__ == '__main__':
    # Obtener puerto del entorno o usar 5000 por defecto
    port = int(os.getenv('PORT', 5000))
    
    # Ejecutar la aplicación
    app.run(host='0.0.0.0', port=port, debug=True)

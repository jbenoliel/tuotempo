from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import logging
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
        "service": "API Centros TuoTempo",
        "status": "online",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

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
        
        if not centers_list:
            return jsonify({"success": True, "message": "No se encontraron centros", "centros": []}), 200
        
        # Filtrar por código postal si se especifica
        if codigo_postal:
            centers_list = [
                centro for centro in centers_list 
                if isinstance(centro, dict) and str(centro.get('cp', '')).strip() == str(codigo_postal).strip()
            ]
        
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

# Importar datetime para el timestamp
from datetime import datetime

if __name__ == '__main__':
    # Obtener puerto del entorno o usar 5000 por defecto
    port = int(os.getenv('PORT', 5000))
    
    # Ejecutar la aplicación
    app.run(host='0.0.0.0', port=port, debug=True)

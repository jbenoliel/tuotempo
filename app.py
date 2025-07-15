# Este archivo es un puente para Railway
# Importa y expone la app Flask desde app_dashboard.py

from app_dashboard import app
import logging
import os

# Configurar logging para depuración
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Registrar los Blueprints de las APIs
try:
    # Importamos la función de registro de APIs que hemos definido en blueprints.py
    from blueprints import register_apis
    
    # Registrar todos los Blueprints de API (tuotempo_api y resultado_api)
    with app.app_context():
        register_apis(app)
    
    # Listar todas las rutas registradas para depuración
    logger.info("=== RUTAS REGISTRADAS EN LA APLICACIÓN ===")
    for rule in app.url_map.iter_rules():
        logger.info(f"Ruta: {rule.rule} - Endpoint: {rule.endpoint} - Métodos: {', '.join(rule.methods)}")
    
    logger.info("APIs registradas correctamente")
    
    # Mostrar información sobre el servicio actual en Railway
    service_name = os.environ.get('RAILWAY_SERVICE_NAME', 'local')
    # Normalizar el nombre del servicio para evitar inconsistencias
    service_name = service_name.lower().replace(' ', '-')
    logger.info(f"Aplicación iniciada en el servicio: {service_name}")
    
except Exception as e:
    logger.error(f"Error al registrar las APIs: {e}")
    import traceback
    logger.error(traceback.format_exc())

# No es necesario nada más, este archivo solo sirve para exponer la app
# para que Railway pueda encontrarla incluso si sigue ignorando el Procfile

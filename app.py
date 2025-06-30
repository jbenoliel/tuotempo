# Este archivo es un puente para Railway
# Importa y expone la app Flask desde app_dashboard.py

from app_dashboard import app
import logging

# Configurar logging para depuración
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar y registrar la API de resultado_llamada
try:
    from api_resultado_llamada import app as api_resultado_app
    from api_resultado_llamada import status, actualizar_resultado, obtener_resultados
    
    # Registrar directamente las funciones de la API
    app.add_url_rule('/api/status', 'api_status', status, methods=['GET'])
    app.add_url_rule('/api/actualizar_resultado', 'api_actualizar_resultado', actualizar_resultado, methods=['POST'])
    app.add_url_rule('/api/obtener_resultados', 'api_obtener_resultados', obtener_resultados, methods=['GET'])
    
    # Registrar también las rutas dinámicamente (para cualquier otra ruta que pueda existir)
    for rule in api_resultado_app.url_map.iter_rules():
        # Saltamos la ruta 'static' y las que ya hemos registrado manualmente
        if rule.endpoint == 'static' or rule.endpoint in ['status', 'actualizar_resultado', 'obtener_resultados']:
            continue
            
        # Obtener la vista (función) asociada a la ruta
        view_func = api_resultado_app.view_functions[rule.endpoint]
        
        # Registrar la ruta en la app principal con un prefijo para evitar conflictos
        app.add_url_rule(
            rule.rule,  # La regla ya incluye el prefijo /api
            endpoint=f"api_{rule.endpoint}",  # Prefijo para evitar conflictos de nombres
            view_func=view_func,
            methods=rule.methods
        )
    
    # Listar todas las rutas registradas para depuración
    logger.info("=== RUTAS REGISTRADAS EN LA APLICACIÓN ===")
    for rule in app.url_map.iter_rules():
        logger.info(f"Ruta: {rule.rule} - Endpoint: {rule.endpoint} - Métodos: {', '.join(rule.methods)}")
    
    logger.info("API de resultado_llamada registrada correctamente")
except Exception as e:
    logger.error(f"Error al registrar API de resultado_llamada: {e}")
    import traceback
    logger.error(traceback.format_exc())

# No es necesario nada más, este archivo solo sirve para exponer la app
# para que Railway pueda encontrarla incluso si sigue ignorando el Procfile

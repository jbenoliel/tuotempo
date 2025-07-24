# Simple safe register_apis function
def register_apis(app):
    """
    Importa y registra todos los Blueprints de las APIs en la aplicación principal.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Lista de APIs que sabemos que existen
    safe_apis = [
        ('api_centros', 'centros_api'),
        ('api_tuotempo', 'tuotempo_api'),
        ('api_resultado_llamada', 'resultado_llamada_api'),
        ('api_pearl_calls', 'api_pearl_calls'),
        ('api_daemon_status', 'daemon_status_api'),
        ('api_railway_verification', 'railway_verification_api')
    ]
    
    for module_name, blueprint_name in safe_apis:
        try:
            module = __import__(module_name, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint)
            logger.info(f"API {module_name} registrada exitosamente")
        except ImportError as e:
            logger.warning(f"No se pudo importar {module_name}: {e}")
        except AttributeError as e:
            logger.warning(f"No se encontró {blueprint_name} en {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error registrando {module_name}: {e}")
    
    logger.info("Proceso de registro de APIs completado")
EOF < /dev/null

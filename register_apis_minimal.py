def register_apis(app):
    """
    Registra solo las APIs que sabemos que existen y funcionan.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # APIs que sabemos que existen
    existing_apis = [
        ('api_centros', 'centros_api', 'API de centros'),
        ('api_tuotempo', 'tuotempo_api', 'API de TuoTempo'),
    ]
    
    for module_name, blueprint_name, description in existing_apis:
        try:
            module = __import__(module_name, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint)
            logger.info(f"{description} registrada correctamente")
        except ImportError as e:
            logger.warning(f"No se pudo importar {module_name}: {e}")
        except AttributeError as e:
            logger.warning(f"No se encontró {blueprint_name} en {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error registrando {description}: {e}")
    
    logger.info("Registro de APIs completado")
EOF < /dev/null

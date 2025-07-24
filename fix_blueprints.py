import re

# Read the file
with open('blueprints.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define existing APIs
existing_apis = [
    'api_centros',
    'api_pearl_calls', 
    'api_resultado_llamada',
    'api_tuotempo',
    'api_daemon_status',
    'api_railway_verification'
]

# Create new register_apis function with safe imports
new_register_function = '''def register_apis(app):
    """
    Importa y registra todos los Blueprints de las APIs en la aplicación principal.
    """
    # Verificar si los blueprints ya están registrados para evitar duplicados
    registered_blueprints = [bp.name for bp in app.blueprints.values()]
    
    # Lista de APIs existentes para importar
    apis_to_import = [
        ('api_resultado_llamada', 'resultado_llamada_api', 'API de resultado de llamada'),
        ('api_centros', 'centros_api', 'API de centros'),
        ('api_tuotempo', 'tuotempo_api', 'API de TuoTempo'),
        ('api_pearl_calls', 'api_pearl_calls', 'API de llamadas Pearl'),
        ('api_daemon_status', 'daemon_status_api', 'API de estado del daemon'),
        ('api_railway_verification', 'railway_verification_api', 'API de verificación de Railway')
    ]
    
    for module_name, blueprint_name, description in apis_to_import:
        try:
            if blueprint_name not in registered_blueprints:
                module = __import__(module_name, fromlist=[blueprint_name])
                blueprint = getattr(module, blueprint_name)
                app.register_blueprint(blueprint)
                logger.info(f"{description} registrada exitosamente")
            else:
                logger.info(f"{description} ya estaba registrada, se omite.")
        except ImportError as e:
            logger.warning(f"No se pudo importar {module_name}: {e}")
        except AttributeError as e:
            logger.warning(f"No se pudo encontrar blueprint {blueprint_name} en {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error inesperado al registrar {description}: {e}")
    
    logger.info("Proceso de registro de APIs completado")'''

# Replace the register_apis function
pattern = r'def register_apis\(app\):.*?(?=\n# --- REGISTRO DE APIS --- < /dev/null | \n@bp\.route|\nclass |\ndef [^r]|\Z)'
content = re.sub(pattern, new_register_function, content, flags=re.DOTALL)

# Write back
with open('blueprints_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('blueprints.py fixed successfully')

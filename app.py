# Este archivo es un puente para Railway
# Importa y expone la app Flask desde app_dashboard.py

from app_dashboard import app

# Importar y registrar la API de resultado_llamada
try:
    from api_resultado_llamada import app as api_resultado_app
    
    # Registrar todas las rutas de api_resultado_llamada en la app principal
    for rule in api_resultado_app.url_map.iter_rules():
        # Obtener la vista (función) asociada a la ruta
        view_func = api_resultado_app.view_functions[rule.endpoint]
        
        # Registrar la ruta en la app principal
        app.add_url_rule(
            rule.rule,
            endpoint=rule.endpoint,
            view_func=view_func,
            methods=rule.methods
        )
    
    print("API de resultado_llamada registrada correctamente")
except Exception as e:
    print(f"Error al registrar API de resultado_llamada: {e}")

# No es necesario nada más, este archivo solo sirve para exponer la app
# para que Railway pueda encontrarla incluso si sigue ignorando el Procfile

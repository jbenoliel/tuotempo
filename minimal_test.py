# Test mínimo de start.py con manejo de errores
import os
import sys

# Simular variables de entorno básicas
os.environ['RAILWAY_SERVICE_NAME'] = 'local'

try:
    from app import app
    print("✓ App importada correctamente")
    
    # Listar rutas para verificar que centros_api está registrado
    print("\nRutas registradas:")
    with app.app_context():
        for rule in app.url_map.iter_rules():
            if 'centro' in str(rule.rule) or 'api' in str(rule.rule):
                print(f"  {rule.rule} -> {rule.endpoint}")
                
except ImportError as e:
    print(f"✗ Error de importación: {e}")
except Exception as e:
    print(f"✗ Error inesperado: {e}")
EOF < /dev/null

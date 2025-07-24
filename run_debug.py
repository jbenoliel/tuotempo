"""
Script simple para iniciar la aplicación Flask en modo debug
con logs detallados para identificar problemas.
"""
import logging
import os
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Cargar variables de entorno
load_dotenv()

# Forzar modo debug
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = 'true'

# Imprimir variables importantes
print("=== VARIABLES DE ENTORNO ===")
for var in ['MYSQLHOST', 'MYSQLPORT', 'MYSQLUSER', 'MYSQLDATABASE']:
    print(f"{var}: {os.getenv(var)}")
print("===========================")

# Importar la app con manejo de errores específico
try:
    print("Intentando importar la aplicación Flask...")
    from app import app
    
    print("Aplicación importada correctamente.")
    print("Iniciando servidor en http://localhost:5000...")
    
    # Iniciar app
    app.run(host='0.0.0.0', port=5000, debug=True)
    
except ImportError as e:
    print(f"Error al importar: {e}")
    print("Detalles del error:", str(e))
    import traceback
    traceback.print_exc()

except Exception as e:
    print(f"Error inesperado: {e}")
    import traceback
    traceback.print_exc()

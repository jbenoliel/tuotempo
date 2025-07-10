import os
import subprocess
import logging
import sys
import time
import threading

# --- CONFIGURACIÓN ---
# Ya no se necesita MIGRATION_SCRIPTS, se descubrirán automáticamente.
CRITICAL_MODULES = {
    'pearl_caller': 'Cliente de API Pearl AI',
    'call_manager': 'Gestor de la cola de llamadas',
    'api_pearl_calls': 'API REST para llamadas',
    'calls_updater': 'Actualizador de estados de llamadas'
}
FRONTEND_FILES = [
    'templates/calls_manager.html',
    'static/css/calls_manager.css',
    'static/js/calls_manager.js',
]
PEARL_ENV_VARS = ['PEARL_ACCOUNT_ID', 'PEARL_SECRET_KEY', 'PEARL_OUTBOUND_ID']

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(processName)s] - %(message)s',
    stream=sys.stdout
)

# --- LÓGICA DE ARRANQUE ---

def run_command(command):
    """Ejecuta un comando y registra su salida."""
    logging.info(f"Ejecutando: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
        if result.stdout: logging.info(f"Salida: {result.stdout.strip()}")
        if result.stderr: logging.warning(f"Errores: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Excepción al ejecutar comando: {e}")
        return False

def run_migrations():
    """Ejecuta el sistema de migración inteligente basado en esquemas."""
    logging.info("--- 1. Iniciando Sistema de Migración Inteligente ---")
    try:
        from db_schema_manager import run_intelligent_migration
        run_intelligent_migration()
    except ImportError as e:
        logging.error(f"No se pudo importar el gestor de esquemas: {e}")
        logging.error("Asegúrate de que 'db_schema_manager.py' existe y no tiene errores.")
    except Exception as e:
        logging.error(f"Ocurrió un error inesperado durante la migración inteligente: {e}")
    logging.info("--- Sistema de Migración Inteligente completado ---")

def verify_deployment():
    """Verifica la integridad del despliegue."""
    logging.info("--- 2. Verificando Integridad del Despliegue ---")
    all_ok = True
    for module, desc in CRITICAL_MODULES.items():
        try:
            __import__(module)
            logging.info(f"  [OK] {desc} ({module})")
        except ImportError as e:
            logging.error(f"  [FALLO] {desc} ({module}): {e}")
            all_ok = False
    for file in FRONTEND_FILES:
        if not os.path.exists(file):
            logging.error(f"  [FALLO] Archivo de frontend no encontrado: {file}")
            all_ok = False
    for var in PEARL_ENV_VARS:
        if not os.getenv(var):
            logging.error(f"  [FALLO] Variable de entorno requerida no definida: {var}")
            all_ok = False
    if not all_ok:
        logging.critical("La verificación del despliegue falló. Abortando.")
        sys.exit(1)
    logging.info("--- Verificación completada exitosamente ---")

def main():
    """Punto de entrada principal. Orquesta el arranque de servicios."""
    run_migrations()
    verify_deployment()

    service_name = os.getenv('RAILWAY_SERVICE_NAME', 'local')
    # Normalizar nombre del servicio para evitar inconsistencias
    service_name = service_name.lower().replace(' ', '-')

    logging.info(f"--- 3. Iniciando servicio: {service_name} ---")

    # Para producción, usamos Gunicorn. Para local, el servidor de desarrollo de Flask.
    use_gunicorn = os.getenv('ENVIRONMENT') == 'production'

    if 'actualizarllamadas' in service_name:
        logging.info("Iniciando el scheduler de actualización de llamadas...")
        from calls_updater import run_scheduler
        run_scheduler()

    elif service_name == 'local':
        logging.info("Entorno local detectado. Iniciando API y scheduler en segundo plano.")
        from calls_updater import run_scheduler
        scheduler_thread = threading.Thread(target=run_scheduler, name="SchedulerThread", daemon=True)
        scheduler_thread.start()
        
        from app import app
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)

    else: # Servicio web principal (web, dashboard, tuotempo-apis, etc.)
        logging.info("Iniciando la aplicación web principal (API Flask)...")
        if use_gunicorn:
            port = os.getenv('PORT', '8080')
            gunicorn_command = [
                'gunicorn', '--bind', f"0.0.0.0:{port}",
                '--workers', '4', '--timeout', '120',
                '--log-level', 'info', 'app:app'
            ]
            logging.info(f"Lanzando Gunicorn: {' '.join(gunicorn_command)}")
            os.execvp('gunicorn', gunicorn_command)
        else:
            from app import app
            app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

if __name__ == "__main__":
    main()

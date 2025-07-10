import os
import subprocess
import logging
import sys
import time

# --- CONFIGURACIÓN ---
# Scripts de migración a ejecutar en orden
MIGRATION_SCRIPTS = [
    'db_migration_add_call_info.py',
    'db_migration_add_call_fields.py',
    # Añadir futuras migraciones aquí
]

# Módulos Python críticos para el sistema de llamadas
CRITICAL_MODULES = {
    'pearl_caller': 'Cliente de API Pearl AI',
    'call_manager': 'Gestor de la cola de llamadas',
    'api_pearl_calls': 'API REST para llamadas',
}

# Archivos de frontend necesarios
FRONTEND_FILES = [
    'templates/calls_manager.html',
    'static/css/calls_manager.css',
    'static/js/calls_manager.js',
]

# Variables de entorno requeridas para Pearl AI
PEARL_ENV_VARS = ['PEARL_ACCOUNT_ID', 'PEARL_SECRET_KEY']

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Railway Start] - %(message)s',
    stream=sys.stdout
)

# --- FUNCIONES AUXILIARES ---
def run_command(command):
    """Ejecuta un comando y registra su salida. No detiene el script si falla."""
    logging.info(f"Ejecutando comando: {' '.join(command)}")
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # No lanzar excepción si falla
            encoding='utf-8'
        )
        if process.stdout:
            logging.info(f"Salida de {' '.join(command)}:\n{process.stdout.strip()}")
        if process.stderr:
            logging.warning(f"Errores de {' '.join(command)}:\n{process.stderr.strip()}")
        if process.returncode != 0:
            logging.error(f"El comando {' '.join(command)} finalizó con código de error {process.returncode}.")
        else:
            logging.info(f"Comando {' '.join(command)} completado exitosamente.")
        return process.returncode == 0
    except FileNotFoundError:
        logging.error(f"Error: El comando '{command[0]}' no se encontró. ¿Está instalado?")
        return False
    except Exception as e:
        logging.error(f"Excepción inesperada al ejecutar {' '.join(command)}: {e}")
        return False


# --- PASOS DE DESPLIEGUE ---
def run_migrations():
    """Ejecuta todas las migraciones de la base de datos definidas en MIGRATION_SCRIPTS."""
    logging.info("--- 1. Ejecutando Migraciones de Base de Datos ---")
    all_migrations_ok = True
    for script in MIGRATION_SCRIPTS:
        logging.info(f"Intentando ejecutar migración: {script}")
        if os.path.exists(script):
            if not run_command(['python', script]):
                # El error ya se ha logueado en run_command, aquí solo advertimos.
                logging.warning(f"La migración {script} podría haber fallado o ya estar aplicada. Revisar logs.")
                # No consideramos esto un fallo fatal, podría ya estar aplicada.
        else:
            logging.warning(f"Script de migración no encontrado: {script}. Saltando.")
    logging.info("--- Migraciones completadas ---")


def verify_deployment():
    """Verifica que todos los componentes críticos del sistema de llamadas estén presentes."""
    logging.info("--- 2. Verificando Integridad del Despliegue ---")
    all_ok = True

    # 1. Verificar módulos Python
    logging.info("Verificando módulos Python...")
    for module_name, description in CRITICAL_MODULES.items():
        try:
            __import__(module_name)
            logging.info(f"  [OK] {description} ({module_name}) cargado.")
        except ImportError as e:
            logging.error(f"  [FALLO] {description} ({module_name}): No se pudo importar. Error: {e}")
            all_ok = False

    # 2. Verificar archivos del frontend
    logging.info("Verificando archivos del frontend...")
    for file_path in FRONTEND_FILES:
        if os.path.exists(file_path):
            logging.info(f"  [OK] Archivo encontrado: {file_path}")
        else:
            logging.error(f"  [FALLO] Archivo de frontend no encontrado: {file_path}")
            all_ok = False

    # 3. Verificar variables de entorno (solo advertencia)
    logging.info("Verificando variables de entorno de Pearl AI...")
    for var in PEARL_ENV_VARS:
        if os.getenv(var):
            logging.info(f"  [OK] Variable de entorno '{var}' configurada.")
        else:
            logging.warning(f"  [AVISO] Variable de entorno '{var}' no está configurada. El sistema de llamadas no funcionará.")
            # No marcamos all_ok como False, ya que el servidor puede arrancar sin esto.

    if all_ok:
        logging.info("✅ Verificación de integridad completada con éxito.")
    else:
        logging.error("❌ Verificación de integridad fallida. Faltan componentes críticos.")
    
    return all_ok


def setup_admin_user():
    """Configura el usuario administrador si el script existe."""
    logging.info("--- 3. Configurando Usuario Administrador ---")
    if os.path.exists('setup_railway.py'):
        run_command(['python', 'setup_railway.py'])
    else:
        logging.info("Script 'setup_railway.py' no encontrado, saltando este paso.")


def start_web_service():
    """Inicia el servicio web principal con Gunicorn."""
    logging.info("--- 4. Iniciando Servicio Web Principal ---")
    port = os.getenv('PORT', '8080')
    gunicorn_command = [
        'gunicorn',
        '--bind', f"0.0.0.0:{port}",
        '--workers', '4',
        '--timeout', '120',
        '--log-level', 'info',
        'api_tuotempo:app'
    ]
    logging.info(f"Lanzando Gunicorn con el comando: {' '.join(gunicorn_command)}")
    try:
        os.execvp('gunicorn', gunicorn_command)
    except FileNotFoundError:
        logging.error("FATAL: El comando 'gunicorn' no se encontró.")
        logging.error("Asegúrate de que gunicorn esté en tu requirements.txt y se haya instalado.")
        sys.exit(1)


# --- PUNTO DE ENTRADA ---
def main():
    """
    Punto de entrada principal para el despliegue en Railway.
    Determina qué servicio ejecutar basado en la variable de entorno RAILWAY_SERVICE_NAME.
    """
    logging.info("=" * 60)
    logging.info("🚄 INICIANDO SCRIPT DE ARRANQUE TUOTEMPO EN RAILWAY")
    logging.info(f"📅 Hora: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    logging.info(f"🐍 Versión de Python: {sys.version.split()[0]}")
    logging.info(f"📁 Directorio de trabajo: {os.getcwd()}")
    logging.info("=" * 60)

    service_name = os.environ.get('RAILWAY_SERVICE_NAME', 'web').lower()
    logging.info(f"Servicio detectado en Railway: '{service_name}'")

    # Mapeo de servicios específicos a sus comandos de inicio
    service_commands = {
        'tuotempo-apis-production': ['gunicorn', 'api_tuotempo:app'],
        'actualizarllamadas': ['gunicorn', 'api_resultado_llamada:app'],
    }

    # Flujo para el servicio web principal (dashboard + APIs)
    if 'web' in service_name or 'dashboard' in service_name:
        logging.info("Iniciando flujo de despliegue para el servicio web principal.")
        run_migrations()
        if not verify_deployment():
            logging.critical("El despliegue no puede continuar debido a fallos en la verificación.")
            sys.exit(1)
        setup_admin_user()
        start_web_service()

    # Flujo para otros servicios definidos
    else:
        command_to_run = None
        for key, command in service_commands.items():
            if key in service_name:
                command_to_run = command
                logging.info(f"Coincidencia encontrada para el servicio '{service_name}'. Se ejecutará el comando para '{key}'.")
                break
        
        if command_to_run:
            logging.info(f"Ejecutando comando para servicio específico: {' '.join(command_to_run)}")
            try:
                os.execvp(command_to_run[0], command_to_run)
            except FileNotFoundError:
                logging.error(f"FATAL: El comando '{command_to_run[0]}' no se encontró.")
                sys.exit(1)
        else:
            logging.error(f"No se encontró una acción definida para el servicio '{service_name}'.")
            logging.info("Servicios específicos disponibles: " + ", ".join(service_commands.keys()))
            sys.exit(1)


if __name__ == "__main__":
    main()

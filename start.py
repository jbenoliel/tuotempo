import os
import subprocess
import logging
import sys
import time
import threading

# --- Bloque de Depuración de Variables de Entorno ---
# Imprime todas las variables de entorno para verificar la configuración en Railway.
logging.info("--- [DEBUG] Mostrando variables de entorno disponibles ---")
for key, value in os.environ.items():
    # Por seguridad, ocultamos valores de variables que parezcan sensibles
    if 'SECRET' in key.upper() or 'PASSWORD' in key.upper() or 'KEY' in key.upper():
        logging.info(f"ENV: {key}=********")
    else:
        logging.info(f"ENV: {key}={value}")
logging.info("--- [DEBUG] Fin de la lista de variables de entorno ---")

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
    """Ejecuta el sistema de migración inteligente. Si falla, detiene el arranque."""
    logging.info("--- 1. Iniciando Sistema de Migración Inteligente ---")
    success = False
    try:
        # Importar aquí para evitar dependencias circulares si el gestor usa logging
        from db_schema_manager import run_intelligent_migration
        
        # Usar variable específica para controlar migración (más robusto que nombres de servicio)
        run_migration = os.environ.get('RUN_MIGRATION', 'true').lower() == 'true'
        service_name = os.environ.get('RAILWAY_SERVICE_NAME', 'local')
        
        # En local siempre ejecutar migración, en Railway usar variable RUN_MIGRATION
        if os.environ.get('RAILWAY_SERVICE_NAME') is None:
            logging.info("Entorno local detectado. Se ejecutará la migración.")
            should_run_migration = True
        else:
            should_run_migration = run_migration
            logging.info(f"Entorno Railway detectado. RUN_MIGRATION={run_migration}")

        if should_run_migration:
            logging.info(f"El servicio '{service_name}' SÍ está configurado para ejecutar la migración.")
            
            # Conectar las variables de la base de datos si no están presentes (para servicios que las necesitan)
            if not all(os.getenv(var) for var in ['MYSQLHOST', 'MYSQLUSER', 'MYSQLPASSWORD', 'MYSQLDATABASE', 'MYSQLPORT']):
                logging.critical("Este servicio debe ejecutar la migración pero no tiene las variables de entorno de la base de datos (ej. MYSQLHOST). Abortando.")
                sys.exit(1)

            if run_intelligent_migration():
                logging.info("✅ Sistema de Migración Inteligente (esquema) completado exitosamente.")
                # Ahora, ejecutar migraciones de datos adicionales
                logging.info("--- Iniciando migraciones de datos adicionales ---")
                try:
                    from db_migration_verify_admin import run_migration as verify_admin_migration
                    if verify_admin_migration():
                        logging.info("✅ Migración de datos 'verify_admin' completada.")
                        success = True # Solo si ambas migraciones tienen éxito
                    else:
                        logging.error("❌ La migración de datos 'verify_admin' falló.")
                        success = False
                except Exception as e:
                    logging.error(f"❌ Error catastrófico durante la migración de datos: {e}")
                    success = False
            else:
                logging.error("❌ El sistema de migración informó de un fallo durante la ejecución.")
                # success sigue siendo False, lo que es correcto para detener el servicio.
        else:
            logging.info(f"El servicio '{service_name}' NO está configurado para ejecutar la migración. Saltando este paso.")
            # Si no se debe ejecutar la migración, se considera un éxito para que el servicio arranque.
            success = True

    except ImportError as e:
        logging.critical(f"FATAL: No se pudo importar 'db_schema_manager'. Error: {e}")
    except Exception as e:
        logging.critical(f"FATAL: Ocurrió un error catastrófico durante la migración: {e}", exc_info=True)
    
    if not success:
        logging.error("--- ⚠️ La migración de la base de datos falló. Continuando con el arranque pero puede haber problemas. ---")
        logging.warning("RECOMENDACIÓN: Revisa los logs de migración y considera ejecutar las migraciones manualmente.")
        # No usar sys.exit(1) para permitir que el servicio arranque y pueda diagnosticarse

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

def run_reservas_automaticas_daemon():
    """Ejecuta el daemon de reservas automáticas en segundo plano."""
    logging.info("[RESERVAS-DAEMON] Iniciando daemon de reservas automáticas...")
    
    # Verificar si el daemon está habilitado
    daemon_enabled = os.getenv('RESERVAS_DAEMON_ENABLED', 'false').lower() == 'true'  # Temporalmente deshabilitado
    if not daemon_enabled:
        logging.info("[RESERVAS-DAEMON] Daemon deshabilitado por variable RESERVAS_DAEMON_ENABLED")
        return
    
    # Verificar variables de entorno necesarias para TuoTempo
    env = os.getenv('TUOTEMPO_ENV', 'PRO').upper()
    api_key = os.getenv(f'TUOTEMPO_API_KEY_{env}')
    instance_id = os.getenv('TUOTEMPO_INSTANCE_ID')
    
    # Si no hay API key en variables de entorno, usar valores predeterminados
    has_tuotempo_config = api_key or instance_id
    
    if not has_tuotempo_config:
        logging.info("[RESERVAS-DAEMON] No se encontraron variables de TuoTempo personalizadas, usando configuración predeterminada")
        logging.info("[RESERVAS-DAEMON] El daemon usará las credenciales integradas en el código")
    else:
        logging.info(f"[RESERVAS-DAEMON] Usando configuración personalizada de TuoTempo para entorno {env}")
    
    try:
        from procesador_reservas_automaticas import ProcesadorReservasAutomaticas
        import time
        from datetime import datetime
        
        procesador = ProcesadorReservasAutomaticas()
        interval_minutes = int(os.getenv('RESERVAS_INTERVAL_MINUTES', '30'))
        
        logging.info(f"[RESERVAS-DAEMON] Daemon iniciado con intervalo de {interval_minutes} minutos")
        logging.info(f"[RESERVAS-DAEMON] Configuración TuoTempo - Entorno: {env}, Instance ID: {instance_id or 'tt_portal_adeslas'}")
        
        while True:
            try:
                start_time = datetime.now()
                logging.info(f"[RESERVAS-DAEMON] --- Iniciando ciclo: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
                
                procesador.procesar_leads_automaticos()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logging.info(f"[RESERVAS-DAEMON] --- Ciclo completado en {duration:.2f} segundos ---")
                
                logging.info(f"[RESERVAS-DAEMON] Esperando {interval_minutes} minutos...")
                time.sleep(interval_minutes * 60)
                
            except Exception as e:
                logging.error(f"[RESERVAS-DAEMON] Error en ciclo de procesamiento: {e}")
                logging.info("[RESERVAS-DAEMON] Esperando 5 minutos antes de reintentar...")
                time.sleep(300)  # 5 minutos
                
    except ImportError as e:
        logging.error(f"[RESERVAS-DAEMON] No se pudo importar procesador de reservas: {e}")
        logging.error("[RESERVAS-DAEMON] Asegúrate de que el archivo procesador_reservas_automaticas.py esté disponible")
    except Exception as e:
        logging.error(f"[RESERVAS-DAEMON] Error fatal en daemon: {e}")
        logging.error("[RESERVAS-DAEMON] El daemon de reservas automáticas no pudo iniciarse")

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
        
        # Iniciar daemon de reservas automáticas en entorno local
        reservas_thread = threading.Thread(target=run_reservas_automaticas_daemon, name="ReservasThread", daemon=True)
        reservas_thread.start()
        
        from app import app
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)

    else: # Servicio web principal (web, dashboard, tuotempo-apis, etc.)
        logging.info("Iniciando la aplicación web principal (Dashboard + API)...")
        
        # Iniciar scheduler de actualización de llamadas Pearl AI
        logging.info("Iniciando scheduler de actualización de llamadas Pearl AI en segundo plano...")
        from calls_updater import run_scheduler
        scheduler_thread = threading.Thread(target=run_scheduler, name="CallsUpdaterThread", daemon=True)
        scheduler_thread.start()
        
        # Iniciar daemon de reservas automáticas como hilo en segundo plano
        logging.info("Iniciando daemon de reservas automáticas en segundo plano...")
        reservas_thread = threading.Thread(target=run_reservas_automaticas_daemon, name="ReservasAutomaticasThread", daemon=True)
        reservas_thread.start()
        
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

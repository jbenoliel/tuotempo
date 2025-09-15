#!/usr/bin/env python3
"""
Daemon mejorado para ejecutar llamadas programadas que respeta completamente
las reglas parametrizables de scheduler_config:

- working_hours_start / working_hours_end
- working_days
- max_attempts
- reschedule_hours
- Todas las demás configuraciones dinámicas

El daemon:
1. Solo ejecuta llamadas durante horarios laborables
2. Refresca la configuración en cada ciclo
3. Respeta días no laborables
4. Es completamente parametrizable
"""

import time
import logging
from datetime import datetime
from typing import Dict, List
from db import get_connection
from call_manager_scheduler_integration import integrate_scheduler_with_call_manager
from call_manager import CallManager
from call_scheduler_multi_timeframes import CallSchedulerMultiTimeframes as CallScheduler

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScheduledCallsDaemon:
    def __init__(self):
        self.scheduler = CallScheduler()
        self.call_manager = None
        self._last_config_refresh = None

    def get_daemon_config(self) -> Dict:
        """
        Obtiene la configuración del daemon desde scheduler_config
        """
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar para obtener configuración del daemon")
            return {
                'scheduled_calls_interval_minutes': 5,
                'daemon_enabled': True,
                'max_calls_per_cycle': 10
            }

        try:
            with conn.cursor() as cursor:
                # Obtener configuraciones específicas del daemon
                daemon_configs = {
                    'scheduled_calls_interval_minutes': 5,
                    'daemon_enabled': True,
                    'max_calls_per_cycle': 10
                }

                for config_key in daemon_configs.keys():
                    cursor.execute(
                        "SELECT config_value FROM scheduler_config WHERE config_key = %s",
                        (config_key,)
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        try:
                            # Intentar convertir a bool para 'daemon_enabled'
                            if config_key == 'daemon_enabled':
                                daemon_configs[config_key] = str(row[0]).lower() in ['true', '1', 'yes', 'on']
                            else:
                                daemon_configs[config_key] = int(row[0])
                        except (ValueError, TypeError):
                            logger.warning(f"Valor inválido para {config_key}: {row[0]}, usando default")

                return daemon_configs

        except Exception as e:
            logger.error(f"Error obteniendo configuración del daemon: {e}")
            return {
                'scheduled_calls_interval_minutes': 5,
                'daemon_enabled': True,
                'max_calls_per_cycle': 10
            }
        finally:
            conn.close()

    def is_daemon_enabled(self) -> bool:
        """Verifica si el daemon está habilitado"""
        config = self.get_daemon_config()
        return config.get('daemon_enabled', True)

    def should_execute_calls(self) -> bool:
        """
        Verifica si se deben ejecutar llamadas ahora:
        - Horarios de funcionamiento
        - Días laborables
        - Estado del daemon
        """
        # Verificar si el daemon está habilitado
        if not self.is_daemon_enabled():
            logger.debug("Daemon deshabilitado por configuración")
            return False

        # Recargar configuración del scheduler
        self.scheduler._config_loaded = False  # Forzar recarga

        # Verificar horarios laborables
        now = datetime.now()
        if not self.scheduler.is_working_time(now):
            working_start, working_end = self.scheduler.get_working_hours()
            weekday = now.strftime('%A')
            logger.debug(f"Fuera de horario laboral: {now.strftime('%H:%M')} el {weekday}. "
                        f"Horario: {working_start}-{working_end}")
            return False

        logger.debug("Daemon habilitado y en horario laboral - ejecutando llamadas")
        return True

    def execute_scheduled_calls(self) -> Dict:
        """
        Ejecuta las llamadas programadas pendientes
        """
        if not self.should_execute_calls():
            return {
                'calls_executed': 0,
                'reason': 'fuera_de_horario_o_deshabilitado',
                'status': 'skipped'
            }

        # Obtener configuración actualizada
        daemon_config = self.get_daemon_config()
        max_calls = daemon_config.get('max_calls_per_cycle', 10)

        # Obtener llamadas pendientes usando la integración existente
        try:
            leads = integrate_scheduler_with_call_manager()[:max_calls]

            if not leads:
                return {
                    'calls_executed': 0,
                    'reason': 'no_pending_calls',
                    'status': 'success'
                }

            logger.info(f"Ejecutando {len(leads)} llamadas programadas")

            # Inicializar call manager si no existe
            if not self.call_manager:
                self.call_manager = CallManager()

            # Ejecutar las llamadas
            result = self.call_manager.start(leads)

            return {
                'calls_executed': len(leads),
                'reason': 'scheduled_calls_processed',
                'status': 'success',
                'details': result
            }

        except Exception as e:
            logger.error(f"Error ejecutando llamadas programadas: {e}")
            return {
                'calls_executed': 0,
                'reason': f'error: {str(e)}',
                'status': 'error'
            }

    def log_scheduler_status(self):
        """
        Log periódico del estado del scheduler para monitoreo con múltiples franjas
        """
        try:
            stats = getattr(self.scheduler, 'get_statistics', lambda: {})()
            time_slots = self.scheduler.get_working_time_slots()

            # Formatear franjas horarias para el log
            slots_str = ", ".join([f"{slot['start']}-{slot['end']}" for slot in time_slots])

            logger.info(f"[SCHEDULER-STATUS] "
                       f"Pending: {stats.get('pending_calls', 'N/A')}, "
                       f"Today: {stats.get('scheduled_today', 'N/A')}, "
                       f"Franjas: {slots_str}")

            # Log franja actual si estamos en horario laboral
            now = datetime.now()
            current_slot = self.scheduler.get_current_working_slot_info(now)
            if current_slot:
                logger.info(f"[CURRENT-SLOT] Actualmente en franja: {current_slot['start']}-{current_slot['end']}")

        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas del scheduler: {e}")

    def run_daemon(self):
        """
        Bucle principal del daemon - completamente parametrizable
        """
        logger.info("🚀 Iniciando Daemon de Llamadas Programadas (Mejorado)")
        logger.info("✅ Respeta horarios laborables y configuración dinámica")

        while True:
            try:
                # Obtener configuración actualizada cada ciclo
                daemon_config = self.get_daemon_config()
                interval_minutes = daemon_config.get('scheduled_calls_interval_minutes', 5)

                # Log estado cada 6 ciclos (30 min si interval es 5)
                cycle_count = getattr(self, '_cycle_count', 0) + 1
                self._cycle_count = cycle_count

                if cycle_count % 6 == 0:
                    self.log_scheduler_status()

                # Ejecutar llamadas si corresponde
                start_time = datetime.now()
                result = self.execute_scheduled_calls()
                end_time = datetime.now()

                duration = (end_time - start_time).total_seconds()

                if result['status'] == 'success' and result['calls_executed'] > 0:
                    logger.info(f"✅ Ejecutadas {result['calls_executed']} llamadas en {duration:.2f}s")
                elif result['status'] == 'skipped':
                    logger.debug(f"⏭️  Ciclo omitido: {result['reason']}")
                elif result['status'] == 'error':
                    logger.error(f"❌ Error en ciclo: {result['reason']}")

                # Esperar hasta el siguiente ciclo
                logger.debug(f"💤 Esperando {interval_minutes} minutos...")
                time.sleep(interval_minutes * 60)

            except KeyboardInterrupt:
                logger.info("🛑 Daemon detenido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error crítico en daemon: {e}")
                logger.info("⏳ Esperando 5 minutos antes de reintentar...")
                time.sleep(300)  # 5 minutos


def run_scheduled_calls_daemon_improved():
    """
    Función de entrada para iniciar el daemon mejorado
    Compatible con el start.py existente
    """
    daemon = ScheduledCallsDaemon()
    daemon.run_daemon()


if __name__ == "__main__":
    # Ejecutar daemon directamente
    run_scheduled_calls_daemon_improved()
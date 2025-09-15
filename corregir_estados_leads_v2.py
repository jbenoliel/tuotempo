#!/usr/bin/env python3
"""
Script mejorado para corregir estados de leads usando las reglas exactas de scheduler_config:
- max_attempts: 6 intentos máximo
- reschedule_hours: 30 horas entre reprogramaciones
- closure_reasons: definidos en la configuración
"""

import logging
import json
from reprogramar_llamadas_simple import get_pymysql_connection

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_scheduler_config():
    """
    Obtiene la configuración actual del scheduler desde la tabla scheduler_config
    """
    conn = get_pymysql_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT config_key, config_value FROM scheduler_config")
            configs = cursor.fetchall()

            config = {}
            for row in configs:
                key = row['config_key']
                value = row['config_value']

                # Intentar parsear JSON si es necesario
                if key in ['closure_reasons', 'working_days']:
                    try:
                        config[key] = json.loads(value)
                    except:
                        config[key] = value
                else:
                    config[key] = value

            return config
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        return None
    finally:
        conn.close()

def reabrir_leads_pendientes():
    """
    Reabre leads que fueron cerrados incorrectamente según las reglas del scheduler_config
    """
    config = get_scheduler_config()
    if not config:
        logger.error("No se pudo obtener la configuración del scheduler")
        return 0

    max_attempts = int(config.get('max_attempts', 6))
    logger.info(f"Usando max_attempts = {max_attempts} desde scheduler_config")

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return 0

    try:
        with conn.cursor() as cursor:
            # Buscar leads que deben reabrirse según las reglas correctas
            cursor.execute("""
                SELECT DISTINCT l.id, l.nombre, l.telefono, l.call_attempts_count,
                       l.closure_reason, pc.status
                FROM leads l
                JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.lead_status = 'closed'
                    AND pc.status IN (5, 7)  -- Busy, NoAnswer
                    AND l.call_attempts_count < %s  -- Menos del máximo permitido
                    AND l.closure_reason NOT IN ('No interesado', 'Cita agendada', 'Cita programada')
                    AND (l.status_level_1 NOT IN ('No Interesado', 'Cita Agendada') OR l.status_level_1 IS NULL)
            """, (max_attempts,))

            leads_to_reopen = cursor.fetchall()
            logger.info(f"Encontrados {len(leads_to_reopen)} leads para reabrir")

            reopened = 0
            for lead in leads_to_reopen:
                status_text = "Busy" if lead['status'] == 5 else "NoAnswer"

                cursor.execute("""
                    UPDATE leads
                    SET lead_status = 'open',
                        closure_reason = NULL,
                        status_level_1 = 'Volver a llamar',
                        selected_for_calling = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                """, (lead['id'],))

                reopened += 1
                logger.info(f"Reabierto lead {lead['id']} - {lead['nombre']} ({status_text}, {lead['call_attempts_count']}/{max_attempts} intentos)")

            conn.commit()
            return reopened

    except Exception as e:
        logger.error(f"Error reabriendo leads: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def cerrar_leads_maximos_intentos():
    """
    Cierra correctamente los leads que han alcanzado el máximo de intentos según scheduler_config
    """
    config = get_scheduler_config()
    if not config:
        logger.error("No se pudo obtener la configuración del scheduler")
        return 0

    max_attempts = int(config.get('max_attempts', 6))
    closure_reasons = config.get('closure_reasons', {})

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return 0

    try:
        with conn.cursor() as cursor:
            # Buscar leads abiertos que han alcanzado el máximo de intentos
            cursor.execute("""
                SELECT DISTINCT l.id, l.nombre, l.telefono, l.call_attempts_count,
                       pc.status, pc.outcome
                FROM leads l
                JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.lead_status = 'open'
                    AND pc.status IN (5, 7)  -- Busy, NoAnswer
                    AND l.call_attempts_count >= %s  -- Máximo alcanzado
                    AND l.status_level_1 != 'No Interesado'
                    AND l.closure_reason IS NULL
            """, (max_attempts,))

            leads_to_close = cursor.fetchall()
            logger.info(f"Encontrados {len(leads_to_close)} leads para cerrar por máximo intentos")

            closed = 0
            for lead in leads_to_close:
                # Determinar la razón de cierre según el último status
                if lead['status'] == 7:  # NoAnswer
                    closure_reason = closure_reasons.get('no_answer', 'Ilocalizable')
                elif lead['status'] == 5:  # Busy
                    closure_reason = closure_reasons.get('no_answer', 'Ilocalizable')  # Usar misma razón que no_answer
                else:
                    closure_reason = 'Ilocalizable'

                cursor.execute("""
                    UPDATE leads
                    SET lead_status = 'closed',
                        closure_reason = %s,
                        selected_for_calling = FALSE,
                        updated_at = NOW()
                    WHERE id = %s
                """, (closure_reason, lead['id']))

                closed += 1
                logger.info(f"Cerrado lead {lead['id']} - {lead['nombre']} ({lead['call_attempts_count']}/{max_attempts} intentos, razón: {closure_reason})")

            conn.commit()
            return closed

    except Exception as e:
        logger.error(f"Error cerrando leads por máximo intentos: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def generar_reporte_final_v2():
    """
    Genera un reporte detallado usando las reglas del scheduler_config
    """
    config = get_scheduler_config()
    max_attempts = int(config.get('max_attempts', 6)) if config else 6

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return

    try:
        with conn.cursor() as cursor:
            print("\n" + "="*70)
            print("REPORTE FINAL - CORRECCIÓN CON REGLAS DE SCHEDULER_CONFIG")
            print("="*70)
            print(f"Reglas aplicadas:")
            if config:
                print(f"  - Máximo intentos: {config.get('max_attempts', 6)}")
                print(f"  - Horas reprogramación: {config.get('reschedule_hours', 30)}h")
                print(f"  - Horario trabajo: {config.get('working_hours_start', '10:00')} - {config.get('working_hours_end', '20:00')}")
            print()

            # Leads por status
            cursor.execute("SELECT lead_status, COUNT(*) as count FROM leads GROUP BY lead_status")
            status_counts = cursor.fetchall()

            for status in status_counts:
                print(f"Leads {status['lead_status'].upper()}: {status['count']}")

            # Distribución de intentos en leads abiertos
            cursor.execute("""
                SELECT
                    call_attempts_count,
                    COUNT(*) as cantidad
                FROM leads
                WHERE lead_status = 'open'
                GROUP BY call_attempts_count
                ORDER BY call_attempts_count
            """)

            attempts_dist = cursor.fetchall()

            print(f"\nDistribución de intentos en leads abiertos:")
            for dist in attempts_dist:
                print(f"  {dist['call_attempts_count']} intentos: {dist['cantidad']} leads")

            # Leads cerrados por razón
            cursor.execute("""
                SELECT
                    closure_reason,
                    COUNT(*) as cantidad
                FROM leads
                WHERE lead_status = 'closed'
                GROUP BY closure_reason
                ORDER BY cantidad DESC
            """)

            closure_dist = cursor.fetchall()

            print(f"\nLeads cerrados por razón:")
            for dist in closure_dist:
                reason = dist['closure_reason'] or '[SIN RAZÓN]'
                print(f"  {reason}: {dist['cantidad']} leads")

    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Iniciando corrección v2 con reglas de scheduler_config...")

    # 1. Obtener y mostrar configuración
    config = get_scheduler_config()
    if config:
        print("Configuración del scheduler:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        print()

    # 2. Reabrir leads que no han alcanzado el máximo
    reopened = reabrir_leads_pendientes()
    print(f"[OK] Leads adicionales reabiertos: {reopened}")

    # 3. Cerrar leads que han alcanzado el máximo
    closed = cerrar_leads_maximos_intentos()
    print(f"[OK] Leads cerrados por máximo intentos: {closed}")

    print(f"\n[RESUMEN] Correcciones v2 realizadas: {reopened + closed}")

    # 4. Reporte final
    generar_reporte_final_v2()

    print("\n[COMPLETADO] Corrección v2 completada!")
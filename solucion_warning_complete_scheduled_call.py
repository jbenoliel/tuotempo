#!/usr/bin/env python3
"""
Solución para el warning: "No se encontró llamada 'pending' para completar para lead XXXX"

PROBLEMA IDENTIFICADO:
- Se llama a complete_scheduled_call() para leads que:
  1. Ya están cerrados (lead_status = 'closed')
  2. No tienen registros en call_schedule
  3. O no tienen llamadas con status = 'pending'

CAUSAS POSIBLES:
1. Concurrencia: Lead se cierra mientras se procesa una llamada
2. Llamadas no programadas que intentan completar schedules inexistentes
3. Desfase temporal en el procesamiento

SOLUCIÓN PROPUESTA:
Mejorar la función complete_scheduled_call para:
1. Verificar si el lead está cerrado antes de intentar completar
2. Reducir el nivel de logging de WARNING a INFO cuando no hay 'pending' calls
3. Agregar más contexto de debugging
"""

import pymysql
import logging
from datetime import datetime
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def mejorar_complete_scheduled_call_analysis():
    """
    Analizar las llamadas que están generando estos warnings
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== ANÁLISIS DE WARNINGS DE COMPLETE_SCHEDULED_CALL ===")

            # 1. Leads cerrados que aún tienen llamadas pending en call_schedule
            print("\n1. LEADS CERRADOS CON LLAMADAS PENDING:")
            cursor.execute("""
                SELECT l.id, l.nombre, l.apellidos, l.lead_status,
                       l.call_attempts_count, l.last_call_attempt,
                       cs.status as schedule_status, cs.scheduled_at,
                       cs.last_outcome
                FROM leads l
                JOIN call_schedule cs ON l.id = cs.lead_id
                WHERE l.lead_status = 'closed'
                AND cs.status = 'pending'
                ORDER BY l.last_call_attempt DESC
                LIMIT 10
            """)

            closed_with_pending = cursor.fetchall()
            if closed_with_pending:
                for lead in closed_with_pending:
                    print(f"Lead {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                    print(f"  Estado: {lead['lead_status']}, Intentos: {lead['call_attempts_count']}")
                    print(f"  Última llamada: {lead['last_call_attempt']}")
                    print(f"  Schedule: {lead['schedule_status']}, Programada: {lead['scheduled_at']}")
                    print("---")
            else:
                print("No hay leads cerrados con llamadas pending.")

            # 2. Llamadas recientes que podrían estar causando warnings
            print("\n2. LLAMADAS RECIENTES A LEADS CERRADOS:")
            cursor.execute("""
                SELECT pc.id as call_id, pc.lead_id, pc.call_time, pc.outcome,
                       l.nombre, l.apellidos, l.lead_status, l.call_attempts_count
                FROM pearl_calls pc
                JOIN leads l ON pc.lead_id = l.id
                WHERE l.lead_status = 'closed'
                AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 2 DAY)
                ORDER BY pc.call_time DESC
                LIMIT 15
            """)

            recent_calls_to_closed = cursor.fetchall()
            if recent_calls_to_closed:
                for call in recent_calls_to_closed:
                    print(f"Call {call['call_id']}: Lead {call['lead_id']} - {call['nombre']} {call['apellidos']}")
                    print(f"  Tiempo: {call['call_time']}, Outcome: {call['outcome']}")
                    print(f"  Lead Status: {call['lead_status']}, Attempts: {call['call_attempts_count']}")
                    print("---")
            else:
                print("No hay llamadas recientes a leads cerrados.")

            # 3. Estadísticas de call_schedule vs pearl_calls
            print("\n3. ESTADÍSTICAS DE INCONSISTENCIAS:")
            cursor.execute("""
                SELECT
                    'Total pearl_calls últimas 24h' as metric,
                    COUNT(*) as count
                FROM pearl_calls
                WHERE call_time >= DATE_SUB(NOW(), INTERVAL 1 DAY)

                UNION ALL

                SELECT
                    'Pearl calls a leads cerrados (24h)' as metric,
                    COUNT(*) as count
                FROM pearl_calls pc
                JOIN leads l ON pc.lead_id = l.id
                WHERE l.lead_status = 'closed'
                AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 1 DAY)

                UNION ALL

                SELECT
                    'Leads con calls pending' as metric,
                    COUNT(DISTINCT lead_id) as count
                FROM call_schedule
                WHERE status = 'pending'

                UNION ALL

                SELECT
                    'Leads cerrados con calls pending' as metric,
                    COUNT(DISTINCT cs.lead_id) as count
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending' AND l.lead_status = 'closed'
            """)

            stats = cursor.fetchall()
            for stat in stats:
                print(f"{stat['metric']}: {stat['count']}")

            # 4. Proponer acciones correctivas
            print("\n4. ACCIONES CORRECTIVAS SUGERIDAS:")
            print("a) Cancelar llamadas pending para leads cerrados:")
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending' AND l.lead_status = 'closed'
            """)

            pending_closed = cursor.fetchone()['count']
            print(f"   - {pending_closed} llamadas pending para leads cerrados que deberían cancelarse")

            print("\nb) Mejorar complete_scheduled_call para:")
            print("   - Verificar estado del lead antes de intentar completar")
            print("   - Reducir nivel de warning cuando es esperado")
            print("   - Cancelar automáticamente calls pending si lead está cerrado")

    except Exception as e:
        logger.error(f"Error en análisis: {e}")
    finally:
        conn.close()

def proposed_fix_complete_scheduled_call():
    """
    Mostrar el código mejorado para complete_scheduled_call
    """

    print("\n=== CÓDIGO MEJORADO PARA COMPLETE_SCHEDULED_CALL ===")
    print("""
def complete_scheduled_call_improved(lead_id: int, outcome: str) -> int:
    '''
    Versión mejorada que maneja mejor los casos edge
    '''
    if not lead_id or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id for complete_scheduled_call: {lead_id}")
        return 0

    conn = None
    try:
        conn = get_pymysql_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD para completar schedule")
            return 0

        with conn.cursor() as cursor:
            # NUEVO: Primero verificar el estado del lead
            cursor.execute('''
                SELECT lead_status, call_attempts_count, nombre, apellidos
                FROM leads
                WHERE id = %s
            ''', (lead_id,))

            lead = cursor.fetchone()
            if not lead:
                logger.warning(f"Lead {lead_id} no existe - no se puede completar schedule")
                return 0

            # NUEVO: Si el lead está cerrado, cancelar cualquier pending call
            if lead['lead_status'] == 'closed':
                cursor.execute('''
                    UPDATE call_schedule
                    SET status = 'cancelled',
                        last_outcome = %s,
                        updated_at = NOW()
                    WHERE lead_id = %s AND status = 'pending'
                ''', (f'lead_closed_{outcome}', lead_id))

                cancelled_count = cursor.rowcount
                if cancelled_count > 0:
                    logger.info(f"Canceladas {cancelled_count} llamadas pending para lead cerrado {lead_id}")
                return cancelled_count

            # Intentar completar llamada pending normalmente
            cursor.execute('''
                UPDATE call_schedule
                SET status = 'completed',
                    last_outcome = %s,
                    updated_at = NOW()
                WHERE lead_id = %s AND status = 'pending'
            ''', (outcome, lead_id))

            updated_count = cursor.rowcount
            conn.commit()

            if updated_count > 0:
                logger.info(f"Completada llamada programada para lead {lead_id} con outcome '{outcome}'")
            else:
                # NUEVO: Nivel INFO en lugar de WARNING y más contexto
                logger.info(f"No hay llamada 'pending' para completar para lead {lead_id} "
                          f"({lead['nombre']} {lead['apellidos']}, status: {lead['lead_status']}, "
                          f"attempts: {lead['call_attempts_count']}). "
                          f"Posiblemente ya fue procesada o cancelada.")

            return updated_count

    except Exception as e:
        logger.error(f"Error completando llamada programada para lead {lead_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return 0

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
    """)

if __name__ == "__main__":
    mejorar_complete_scheduled_call_analysis()
    proposed_fix_complete_scheduled_call()
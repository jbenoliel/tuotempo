#!/usr/bin/env python3
"""
Script para investigar el warning del lead 2467 sobre llamadas 'pending' no encontradas
"""

import pymysql
import logging
from datetime import datetime, timedelta
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

def investigate_lead_2467():
    """Investigar el estado del lead 2467 y sus llamadas programadas"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Información básica del lead 2467
            print("=== INFORMACIÓN DEL LEAD 2467 ===")
            cursor.execute("""
                SELECT id, nombre, apellidos, telefono, lead_status,
                       call_attempts_count, last_call_attempt,
                       selected_for_calling, call_status
                FROM leads
                WHERE id = 2467
            """)
            lead = cursor.fetchone()

            if not lead:
                print("LEAD 2467 NO ENCONTRADO")
                return

            for key, value in lead.items():
                print(f"{key}: {value}")

            # 2. Historial de llamadas programadas para este lead
            print("\n=== HISTORIAL CALL_SCHEDULE PARA LEAD 2467 ===")
            cursor.execute("""
                SELECT id, lead_id, scheduled_at, attempt_number, status,
                       last_outcome
                FROM call_schedule
                WHERE lead_id = 2467
                ORDER BY id DESC
                LIMIT 10
            """)
            schedules = cursor.fetchall()

            if schedules:
                for schedule in schedules:
                    print(f"Schedule ID: {schedule['id']}")
                    print(f"  Status: {schedule['status']}")
                    print(f"  Scheduled: {schedule['scheduled_at']}")
                    print(f"  Attempt: {schedule['attempt_number']}")
                    print(f"  Outcome: {schedule['last_outcome']}")
                    print("---")
            else:
                print("NO HAY REGISTROS EN CALL_SCHEDULE PARA LEAD 2467")

            # 3. Llamadas 'pending' actuales para este lead
            print("\n=== LLAMADAS PENDING ACTUALES PARA LEAD 2467 ===")
            cursor.execute("""
                SELECT COUNT(*) as pending_count
                FROM call_schedule
                WHERE lead_id = 2467 AND status = 'pending'
            """)
            pending = cursor.fetchone()
            print(f"Llamadas pending: {pending['pending_count']}")

            # 4. Buscar patrones similares en otros leads
            print("\n=== LEADS CON PATRONES SIMILARES (últimos 50 con warnings similares) ===")
            cursor.execute("""
                SELECT l.id, l.nombre, l.apellidos, l.lead_status,
                       l.call_attempts_count,
                       COUNT(cs.id) as total_schedules,
                       SUM(CASE WHEN cs.status = 'pending' THEN 1 ELSE 0 END) as pending_schedules,
                       SUM(CASE WHEN cs.status = 'completed' THEN 1 ELSE 0 END) as completed_schedules,
                       SUM(CASE WHEN cs.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_schedules
                FROM leads l
                LEFT JOIN call_schedule cs ON l.id = cs.lead_id
                WHERE l.id BETWEEN 2460 AND 2470
                GROUP BY l.id
                ORDER BY l.id
            """)
            similar_leads = cursor.fetchall()

            for lead_info in similar_leads:
                print(f"Lead {lead_info['id']}: {lead_info['nombre']} {lead_info['apellidos']}")
                print(f"  Status: {lead_info['lead_status']}, Attempts: {lead_info['call_attempts_count']}")
                print(f"  Schedules - Total: {lead_info['total_schedules']}, "
                      f"Pending: {lead_info['pending_schedules']}, "
                      f"Completed: {lead_info['completed_schedules']}, "
                      f"Cancelled: {lead_info['cancelled_schedules']}")
                print("---")

            # 5. Buscar en pearl_calls llamadas recientes al lead 2467
            print("\n=== LLAMADAS RECIENTES EN PEARL_CALLS PARA LEAD 2467 ===")
            try:
                cursor.execute("""
                    SELECT id, lead_id, call_time, outcome
                    FROM pearl_calls
                    WHERE lead_id = 2467
                    ORDER BY call_time DESC
                    LIMIT 5
                """)
                pearl_calls = cursor.fetchall()

                if pearl_calls:
                    for call in pearl_calls:
                        print(f"Pearl Call ID: {call['id']}")
                        print(f"  Call Time: {call['call_time']}")
                        print(f"  Outcome: {call['outcome']}")
                        print("---")
                else:
                    print("NO HAY LLAMADAS EN PEARL_CALLS PARA LEAD 2467")

            except Exception as e:
                print(f"Error consultando pearl_calls: {e}")

            # 6. Buscar problemas de concurrencia
            print("\n=== ANÁLISIS DE CONCURRENCIA ===")
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM call_schedule WHERE status = 'pending') as total_pending,
                    (SELECT COUNT(*) FROM call_schedule WHERE status = 'completed') as total_completed,
                    (SELECT COUNT(*) FROM call_schedule WHERE status = 'cancelled') as total_cancelled,
                    (SELECT COUNT(*) FROM leads WHERE lead_status = 'closed') as closed_leads,
                    (SELECT COUNT(*) FROM leads WHERE selected_for_calling = TRUE) as selected_leads
            """)
            stats = cursor.fetchone()

            for key, value in stats.items():
                print(f"{key}: {value}")

    except Exception as e:
        logger.error(f"Error en investigación: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    investigate_lead_2467()
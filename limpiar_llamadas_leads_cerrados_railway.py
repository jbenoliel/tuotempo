#!/usr/bin/env python3
"""
Script para limpiar llamadas programadas de leads cerrados en Railway
Esto ayuda a reducir warnings innecesarios
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

def cleanup_closed_leads_schedules():
    """
    Cancela todas las llamadas programadas para leads cerrados
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== LIMPIEZA DE LLAMADAS PARA LEADS CERRADOS ===")

            # 1. Encontrar llamadas programadas para leads cerrados
            cursor.execute("""
                SELECT cs.id, cs.lead_id, cs.scheduled_at, cs.attempt_number,
                       l.nombre, l.apellidos, l.closure_reason, l.call_attempts_count
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                AND l.lead_status = 'closed'
                ORDER BY cs.scheduled_at
            """)

            pending_for_closed = cursor.fetchall()

            if not pending_for_closed:
                print("No hay llamadas programadas para leads cerrados. Sistema limpio.")
                return 0

            print(f"Encontradas {len(pending_for_closed)} llamadas programadas para leads cerrados:")

            for schedule in pending_for_closed:
                print(f"  Schedule {schedule['id']}: Lead {schedule['lead_id']} - "
                      f"{schedule['nombre']} {schedule['apellidos']} "
                      f"(Programada: {schedule['scheduled_at']}, "
                      f"Intento: {schedule['attempt_number']}, "
                      f"Cerrado por: {schedule['closure_reason']})")

            # 2. Confirmar cancelación
            print(f"\nSe cancelarán {len(pending_for_closed)} llamadas programadas para leads cerrados.")

            # 3. Cancelar todas las llamadas
            cursor.execute("""
                UPDATE call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                SET cs.status = 'cancelled',
                    cs.last_outcome = 'lead_closed_cleanup',
                    cs.updated_at = NOW()
                WHERE cs.status = 'pending'
                AND l.lead_status = 'closed'
            """)

            cancelled_count = cursor.rowcount
            conn.commit()

            print(f"\nCanceladas {cancelled_count} llamadas programadas para leads cerrados.")

            # 4. Estadísticas finales
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM call_schedule WHERE status = 'pending') as pending_total,
                    (SELECT COUNT(*) FROM call_schedule WHERE status = 'cancelled') as cancelled_total,
                    (SELECT COUNT(*) FROM call_schedule WHERE status = 'completed') as completed_total
            """)

            stats = cursor.fetchone()
            print(f"\nEstadísticas finales de call_schedule:")
            print(f"  Pending: {stats['pending_total']}")
            print(f"  Cancelled: {stats['cancelled_total']}")
            print(f"  Completed: {stats['completed_total']}")

            return cancelled_count

    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    resultado = cleanup_closed_leads_schedules()
    print(f"\nLimpieza completada. Canceladas {resultado} llamadas.")
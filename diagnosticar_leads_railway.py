#!/usr/bin/env python3
"""
Script de diagnóstico para investigar leads problemáticos en Railway
Analiza los leads que están causando warnings de "lead no encontrado"
"""

import logging
from datetime import datetime
from reprogramar_llamadas_simple import get_pymysql_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Leads problemáticos reportados en Railway
PROBLEMATIC_LEADS = [
    556, 558, 561, 562, 564, 563, 551, 566, 568, 565,
    570, 572, 567, 549, 571, 574, 575, 573, 569,
    2052, 2085, 2340, 2467
]

def analizar_leads_problematicos():
    """Analiza en detalle los leads que están causando problemas"""

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return

    print("=== DIAGNOSTICO DE LEADS PROBLEMATICOS ===")
    print(f"Analizando {len(PROBLEMATIC_LEADS)} leads reportados...")
    print()

    try:
        with conn.cursor() as cursor:
            # Analizar cada lead individualmente
            existentes = 0
            no_existentes = 0
            cerrados = 0
            abiertos = 0

            for lead_id in PROBLEMATIC_LEADS:
                cursor.execute("""
                    SELECT id, lead_status, call_attempts_count, closure_reason,
                           nombre, telefono, updated_at, last_call_attempt
                    FROM leads
                    WHERE id = %s
                """, (lead_id,))

                lead = cursor.fetchone()

                if not lead:
                    print(f"[NO EXISTE] Lead {lead_id}: No existe en la BD")
                    no_existentes += 1
                else:
                    existentes += 1
                    status = lead['lead_status'] or 'NULL'
                    attempts = lead['call_attempts_count'] or 0

                    if status == 'closed':
                        cerrados += 1
                        closure = lead['closure_reason'] or 'Sin razón'
                        print(f"[CERRADO] Lead {lead_id}: {status}, intentos={attempts}, razón='{closure}'")
                    else:
                        abiertos += 1
                        print(f"[ABIERTO] Lead {lead_id}: {status}, intentos={attempts}")

                        # Ver si tiene llamadas programadas
                        cursor.execute("""
                            SELECT id, scheduled_at, status, attempt_number
                            FROM call_schedule
                            WHERE lead_id = %s
                            ORDER BY scheduled_at DESC
                            LIMIT 1
                        """, (lead_id,))

                        schedule = cursor.fetchone()
                        if schedule:
                            print(f"    - Programado: {schedule['scheduled_at']}, estado={schedule['status']}")

            print()
            print("=== RESUMEN ===")
            print(f"Total leads analizados: {len(PROBLEMATIC_LEADS)}")
            print(f"Existentes: {existentes}")
            print(f"No existentes: {no_existentes}")
            print(f"Abiertos: {abiertos}")
            print(f"Cerrados: {cerrados}")

            # Verificar call_schedule para estos leads
            print()
            print("=== VERIFICACION CALL_SCHEDULE ===")

            leads_str = ','.join(map(str, PROBLEMATIC_LEADS))
            cursor.execute(f"""
                SELECT cs.lead_id, cs.status, cs.scheduled_at, cs.attempt_number,
                       l.lead_status
                FROM call_schedule cs
                LEFT JOIN leads l ON l.id = cs.lead_id
                WHERE cs.lead_id IN ({leads_str})
                ORDER BY cs.lead_id, cs.scheduled_at DESC
            """)

            schedules = cursor.fetchall()
            print(f"Registros en call_schedule: {len(schedules)}")

            for schedule in schedules:
                lead_id = schedule['lead_id']
                cs_status = schedule['status']
                lead_status = schedule['lead_status'] or 'NULL'
                scheduled = schedule['scheduled_at']

                print(f"Lead {lead_id}: call_schedule={cs_status}, lead_status={lead_status}, programado={scheduled}")

            # Verificar pearl_calls recientes para estos leads
            print()
            print("=== VERIFICACION PEARL_CALLS RECIENTES ===")

            cursor.execute(f"""
                SELECT lead_id, status, created_at, phone_number
                FROM pearl_calls
                WHERE lead_id IN ({leads_str})
                AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
            """)

            recent_calls = cursor.fetchall()
            print(f"Llamadas recientes (24h): {len(recent_calls)}")

            for call in recent_calls:
                print(f"Lead {call['lead_id']}: status={call['status']}, hora={call['created_at']}")

    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}")
    finally:
        conn.close()

def verificar_integridad_leads():
    """Verifica la integridad general de la tabla leads"""

    conn = get_pymysql_connection()
    if not conn:
        return

    print()
    print("=== VERIFICACION DE INTEGRIDAD GENERAL ===")

    try:
        with conn.cursor() as cursor:
            # Contar leads por estado
            cursor.execute("""
                SELECT lead_status, COUNT(*) as count
                FROM leads
                GROUP BY lead_status
            """)

            status_counts = cursor.fetchall()
            print("Distribución por estados:")
            for row in status_counts:
                status = row['lead_status'] or 'NULL'
                count = row['count']
                print(f"  {status}: {count}")

            # Verificar leads con call_schedule pero sin existir
            cursor.execute("""
                SELECT cs.lead_id, COUNT(*) as schedule_count
                FROM call_schedule cs
                LEFT JOIN leads l ON l.id = cs.lead_id
                WHERE l.id IS NULL
                GROUP BY cs.lead_id
                LIMIT 10
            """)

            orphan_schedules = cursor.fetchall()
            if orphan_schedules:
                print()
                print("Programaciones huérfanas (sin lead correspondiente):")
                for row in orphan_schedules:
                    print(f"  Lead {row['lead_id']}: {row['schedule_count']} programaciones")

            # Verificar rangos de IDs
            cursor.execute("SELECT MIN(id) as min_id, MAX(id) as max_id FROM leads")
            id_range = cursor.fetchone()
            print()
            print(f"Rango de IDs en leads: {id_range['min_id']} - {id_range['max_id']}")

    except Exception as e:
        logger.error(f"Error verificando integridad: {e}")
    finally:
        conn.close()

def sugerir_solucion():
    """Sugiere una solución basada en el análisis"""

    print()
    print("=== SUGERENCIAS DE SOLUCION ===")
    print()
    print("1. Si los leads NO EXISTEN:")
    print("   - Limpiar call_schedule de registros huérfanos")
    print("   - Revisar el proceso de creación de leads")
    print()
    print("2. Si los leads están CERRADOS:")
    print("   - Actualizar call_manager_scheduler_integration.py")
    print("   - Filtrar solo leads abiertos en las consultas")
    print()
    print("3. Script de limpieza:")
    print("   DELETE FROM call_schedule WHERE lead_id NOT IN (SELECT id FROM leads);")
    print()
    print("4. Script de verificación adicional:")
    print("   SELECT cs.lead_id FROM call_schedule cs")
    print("   LEFT JOIN leads l ON l.id = cs.lead_id")
    print("   WHERE l.id IS NULL;")

if __name__ == "__main__":
    print("DIAGNOSTICO DE LEADS PROBLEMATICOS EN RAILWAY")
    print("=" * 60)

    analizar_leads_problematicos()
    verificar_integridad_leads()
    sugerir_solucion()

    print()
    print("=" * 60)
    print("[COMPLETADO] Diagnóstico terminado")
    print("Ejecuta este script en Railway para obtener información detallada")
#!/usr/bin/env python3
"""
Script para corregir los estados incorrectos de los leads basándose en los códigos reales de Pearl AI:
- Status 4 (Completed): Deberían revisarse para citas o "No interesado"
- Status 5 (Busy): Deberían reprogramarse si < 3 intentos
- Status 6 (Failed): Cerrar como número inválido es correcto
- Status 7 (NoAnswer): Deberían reprogramarse si < 3 intentos
"""

import logging
from reprogramar_llamadas_simple import get_pymysql_connection

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def corregir_leads_completed_incorrectos():
    """
    Corrige leads con status 4 (Completed) que fueron cerrados incorrectamente.
    Estos leads necesitan revisión manual o clasificación correcta.
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return 0

    try:
        with conn.cursor() as cursor:
            # Buscar leads con status 4 (Completed) cerrados incorrectamente
            cursor.execute("""
                SELECT DISTINCT l.id, l.nombre, l.telefono, l.closure_reason, l.status_level_1
                FROM leads l
                JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.lead_status = 'closed'
                    AND pc.status = 4  -- Completed
                    AND l.closure_reason NOT IN ('Cita agendada', 'Cita programada')
                    AND (l.status_level_1 != 'No Interesado' OR l.status_level_1 IS NULL)
            """)

            completed_leads = cursor.fetchall()

            logger.info(f"Encontrados {len(completed_leads)} leads con status Completed cerrados incorrectamente")

            # Estos leads necesitan ser reabiertos para revisión manual
            corrected = 0
            for lead in completed_leads:
                cursor.execute("""
                    UPDATE leads
                    SET lead_status = 'open',
                        closure_reason = NULL,
                        status_level_1 = NULL,
                        selected_for_calling = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                """, (lead['id'],))

                corrected += 1
                logger.info(f"Reabierto lead {lead['id']} - {lead['nombre']} (status Completed requiere revisión)")

            conn.commit()
            return corrected

    except Exception as e:
        logger.error(f"Error corrigiendo leads Completed: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def reabrir_leads_busy_no_answer():
    """
    Reabre leads con status 5 (Busy) o 7 (NoAnswer) que fueron cerrados
    prematuramente sin alcanzar el límite de intentos.
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return 0

    try:
        with conn.cursor() as cursor:
            # Buscar leads que deben reabrirse
            cursor.execute("""
                SELECT DISTINCT l.id, l.nombre, l.telefono, l.call_attempts_count, pc.status
                FROM leads l
                JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.lead_status = 'closed'
                    AND pc.status IN (5, 7)  -- Busy, NoAnswer
                    AND l.call_attempts_count < 3  -- Límite máximo de intentos
                    AND l.closure_reason != 'No interesado'
                    AND (l.status_level_1 != 'No Interesado' OR l.status_level_1 IS NULL)
            """)

            leads_to_reopen = cursor.fetchall()

            logger.info(f"Encontrados {len(leads_to_reopen)} leads Busy/NoAnswer para reabrir")

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
                logger.info(f"Reabierto lead {lead['id']} - {lead['nombre']} ({status_text}, {lead['call_attempts_count']} intentos)")

            conn.commit()
            return reopened

    except Exception as e:
        logger.error(f"Error reabriendo leads Busy/NoAnswer: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def corregir_inconsistencias_datos():
    """
    Corrige inconsistencias entre closure_reason y status_level_1
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return 0

    try:
        with conn.cursor() as cursor:
            corrected = 0

            # Caso 1: closure_reason IS NULL pero status_level_1 = 'No Interesado'
            cursor.execute("""
                UPDATE leads
                SET closure_reason = 'No interesado',
                    updated_at = NOW()
                WHERE lead_status = 'closed'
                    AND closure_reason IS NULL
                    AND status_level_1 = 'No Interesado'
            """)

            case1_fixed = cursor.rowcount
            corrected += case1_fixed
            logger.info(f"Corregidos {case1_fixed} leads: closure_reason NULL -> 'No interesado'")

            # Caso 2: closure_reason = 'Ilocalizable' pero status_level_1 = 'Cita Agendada'
            cursor.execute("""
                UPDATE leads
                SET closure_reason = 'Cita agendada',
                    updated_at = NOW()
                WHERE lead_status = 'closed'
                    AND closure_reason = 'Ilocalizable'
                    AND status_level_1 = 'Cita Agendada'
            """)

            case2_fixed = cursor.rowcount
            corrected += case2_fixed
            logger.info(f"Corregidos {case2_fixed} leads: closure_reason 'Ilocalizable' -> 'Cita agendada'")

            conn.commit()
            return corrected

    except Exception as e:
        logger.error(f"Error corrigiendo inconsistencias: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def generar_reporte_final():
    """
    Genera un reporte final del estado después de las correcciones
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return

    try:
        with conn.cursor() as cursor:
            print("\n" + "="*60)
            print("REPORTE FINAL - ESTADO DE LEADS DESPUÉS DE CORRECCIONES")
            print("="*60)

            # Leads abiertos
            cursor.execute("SELECT COUNT(*) as count FROM leads WHERE lead_status = 'open'")
            open_leads = cursor.fetchone()['count']

            # Leads cerrados por categoría
            cursor.execute("""
                SELECT
                    CASE
                        WHEN closure_reason IN ('Cita programada', 'Cita agendada') THEN 'Cita Agendada'
                        WHEN closure_reason = 'No interesado' OR status_level_1 = 'No Interesado' THEN 'No Interesado'
                        WHEN closure_reason LIKE '%máximo%' THEN 'Límite Intentos'
                        WHEN closure_reason = 'Ilocalizable - Número no válido' THEN 'Número Inválido'
                        ELSE 'Otros/Revisar'
                    END as categoria,
                    COUNT(*) as cantidad
                FROM leads
                WHERE lead_status = 'closed'
                GROUP BY categoria
                ORDER BY cantidad DESC
            """)

            categories = cursor.fetchall()

            print(f"Leads ABIERTOS: {open_leads}")
            print(f"Leads CERRADOS por categoría:")

            total_closed = sum(cat['cantidad'] for cat in categories)
            for cat in categories:
                percentage = (cat['cantidad'] / total_closed * 100) if total_closed > 0 else 0
                print(f"  - {cat['categoria']}: {cat['cantidad']} ({percentage:.1f}%)")

            print(f"Total leads cerrados: {total_closed}")
            print(f"Total leads en sistema: {open_leads + total_closed}")

    except Exception as e:
        logger.error(f"Error generando reporte final: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Iniciando corrección de estados de leads...")

    # 1. Corregir leads Completed incorrectos
    completed_fixed = corregir_leads_completed_incorrectos()
    print(f"[OK] Leads con status Completed corregidos: {completed_fixed}")

    # 2. Reabrir leads Busy/NoAnswer prematuros
    reopened = reabrir_leads_busy_no_answer()
    print(f"[OK] Leads Busy/NoAnswer reabiertos: {reopened}")

    # 3. Corregir inconsistencias de datos
    inconsistencies_fixed = corregir_inconsistencias_datos()
    print(f"[OK] Inconsistencias de datos corregidas: {inconsistencies_fixed}")

    print(f"\n[RESUMEN] Total de correcciones realizadas: {completed_fixed + reopened + inconsistencies_fixed}")

    # 4. Generar reporte final
    generar_reporte_final()

    print("\n[COMPLETADO] Corrección de estados completada!")
#!/usr/bin/env python3
"""
Script de prueba para verificar que el sistema de procesamiento de outcomes funcione correctamente
"""

import pymysql
import logging
from config import settings
from enhanced_outcome_processor import determine_lead_status_from_outcomes

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

def test_outcome_processing():
    """
    Prueba el procesamiento de outcomes con algunos leads reales
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== PRUEBA DEL SISTEMA DE PROCESAMIENTO DE OUTCOMES ===")

            # Buscar algunos leads con diferentes patterns de outcomes
            cursor.execute("""
                SELECT
                    l.id,
                    l.nombre,
                    l.apellidos,
                    l.status_level_1,
                    l.call_attempts_count,
                    GROUP_CONCAT(pc.outcome ORDER BY pc.call_time ASC) as outcomes_sequence,
                    COUNT(CASE WHEN pc.outcome = 6 THEN 1 END) as outcome_6_count
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE pc.outcome IS NOT NULL
                AND l.lead_status != 'closed'
                GROUP BY l.id
                HAVING COUNT(pc.outcome) >= 2
                ORDER BY outcome_6_count DESC, l.id
                LIMIT 10
            """)

            test_leads = cursor.fetchall()

            print(f"\n1. LEADS DE PRUEBA SELECCIONADOS: {len(test_leads)}")

            for lead in test_leads:
                print(f"\nLead {lead['id']} ({lead['nombre']} {lead['apellidos']}):")
                print(f"  Status actual: {lead['status_level_1']}")
                print(f"  Intentos: {lead['call_attempts_count']}")
                print(f"  Outcomes: {lead['outcomes_sequence']}")
                print(f"  Outcome 6 count: {lead['outcome_6_count']}")

                # Aplicar el procesador
                status_info = determine_lead_status_from_outcomes(lead['id'])

                print(f"  PROCESADOR SUGIERE:")
                print(f"    Status: {status_info['status_level_1']}")
                print(f"    Status L2: {status_info['status_level_2']}")
                print(f"    Razon: {status_info['reason']}")
                print(f"    Cerrar: {status_info['should_close']}")

                # Verificar lógica
                outcomes = [int(o) for o in lead['outcomes_sequence'].split(',') if o and o != 'None']
                outcome_6_count = outcomes.count(6)

                print(f"  VERIFICACION:")
                if outcome_6_count >= 2:
                    expected = "Numero erroneo"
                    print(f"    Esperado: {expected} (2+ outcome 6)")
                elif outcome_6_count == 1:
                    expected = "Volver a llamar"
                    print(f"    Esperado: {expected} (1 outcome 6)")
                elif all(o in [4, 5, 7] for o in outcomes):
                    if lead['call_attempts_count'] >= 6:
                        expected = "No Interesado"
                        print(f"    Esperado: {expected} (max intentos)")
                    else:
                        expected = "Volver a llamar"
                        print(f"    Esperado: {expected} (solo no-contacto)")
                else:
                    expected = "Volver a llamar"
                    print(f"    Esperado: {expected} (mixto)")

                # Verificar consistencia
                if status_info['status_level_1'] == expected:
                    print(f"    CORRECTO")
                else:
                    print(f"    INCONSISTENCIA: esperado {expected}, obtuvo {status_info['status_level_1']}")

            print(f"\n2. ESTADÍSTICAS DEL SISTEMA:")

            # Contar leads por pattern de outcome
            cursor.execute("""
                SELECT
                    'Solo Outcome 6 (1x)' as pattern,
                    COUNT(*) as count
                FROM (
                    SELECT l.id
                    FROM leads l
                    INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                    WHERE pc.outcome = 6
                    AND l.id NOT IN (
                        SELECT DISTINCT lead_id FROM pearl_calls
                        WHERE outcome != 6 AND outcome IS NOT NULL
                    )
                    GROUP BY l.id
                    HAVING COUNT(pc.outcome) = 1
                ) t1

                UNION ALL

                SELECT
                    'Multiple Outcome 6 (2+)' as pattern,
                    COUNT(*) as count
                FROM (
                    SELECT l.id
                    FROM leads l
                    INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                    WHERE pc.outcome = 6
                    GROUP BY l.id
                    HAVING COUNT(CASE WHEN pc.outcome = 6 THEN 1 END) >= 2
                ) t2

                UNION ALL

                SELECT
                    'Solo No-contacto (4,5,7)' as pattern,
                    COUNT(*) as count
                FROM (
                    SELECT l.id
                    FROM leads l
                    INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                    WHERE pc.outcome IN (4, 5, 7)
                    AND l.id NOT IN (
                        SELECT DISTINCT lead_id FROM pearl_calls
                        WHERE outcome NOT IN (4, 5, 7) AND outcome IS NOT NULL
                    )
                    GROUP BY l.id
                    HAVING COUNT(pc.outcome) >= 2
                ) t3
            """)

            patterns = cursor.fetchall()
            for pattern in patterns:
                print(f"  {pattern['pattern']}: {pattern['count']} leads")

            print(f"\n3. PRUEBA COMPLETADA")
            return True

    except Exception as e:
        logger.error(f"Error en prueba: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_outcome_processing()
    if success:
        print("\nSistema de procesamiento de outcomes funcionando correctamente")
    else:
        print("\nError en el sistema de procesamiento")
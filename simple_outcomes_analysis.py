#!/usr/bin/env python3
"""
Script simple para mostrar exactamente qué outcomes tiene cada lead huérfano
"""

import pymysql
import logging
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

def simple_outcomes_analysis():
    """Análisis simple de outcomes de los 31 leads huérfanos"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== ANÁLISIS SIMPLE DE OUTCOMES DE LEADS HUÉRFANOS ===")

            # IDs de los leads huérfanos
            leads_huerfanos_ids = [1971, 1985, 1989, 2000, 2002, 2005, 2072, 2090, 2092, 2094, 2098, 2108, 2132, 2147, 2157, 2162, 2186, 2243, 2261, 2264, 2273, 2280, 2315, 2323, 2328, 2372, 2388, 2399, 2405, 2407, 2422]

            outcomes_stats = {}

            for lead_id in leads_huerfanos_ids:
                # Obtener outcomes del lead
                cursor.execute("""
                    SELECT outcome, COUNT(*) as count
                    FROM pearl_calls
                    WHERE lead_id = %s
                    AND outcome IS NOT NULL
                    GROUP BY outcome
                    ORDER BY outcome
                """, (lead_id,))

                outcomes_lead = cursor.fetchall()
                outcomes_dict = {row['outcome']: row['count'] for row in outcomes_lead}

                # Mostrar outcomes del lead
                outcomes_str = ", ".join([f"{outcome}:{count}" for outcome, count in outcomes_dict.items()])
                print(f"Lead {lead_id}: {outcomes_str}")

                # Contar para estadísticas generales
                for outcome, count in outcomes_dict.items():
                    if outcome not in outcomes_stats:
                        outcomes_stats[outcome] = 0
                    outcomes_stats[outcome] += count

            # Mostrar estadísticas generales
            print(f"\n=== ESTADÍSTICAS GENERALES DE OUTCOMES ===")
            for outcome in sorted(outcomes_stats.keys()):
                count = outcomes_stats[outcome]
                outcome_name = ""
                if outcome == 4:
                    outcome_name = "Ocupado"
                elif outcome == 5:
                    outcome_name = "Colgó"
                elif outcome == 6:
                    outcome_name = "Failed"
                elif outcome == 7:
                    outcome_name = "No contesta"
                else:
                    outcome_name = f"Desconocido_{outcome}"

                print(f"Outcome {outcome} ({outcome_name}): {count} llamadas")

            # Análisis por lead específico
            print(f"\n=== ANÁLISIS POR LEAD ESPECÍFICO ===")

            for lead_id in leads_huerfanos_ids[:10]:  # Solo primeros 10 para no saturar
                cursor.execute("""
                    SELECT
                        l.nombre, l.apellidos, l.call_attempts_count,
                        GROUP_CONCAT(pc.outcome ORDER BY pc.call_time) as outcomes_secuencia
                    FROM leads l
                    LEFT JOIN pearl_calls pc ON l.id = pc.lead_id
                    WHERE l.id = %s
                    GROUP BY l.id
                """, (lead_id,))

                lead_detail = cursor.fetchone()
                outcomes_seq = lead_detail['outcomes_secuencia']

                print(f"Lead {lead_id} ({lead_detail['nombre']} {lead_detail['apellidos']}):")
                print(f"  Attempts: {lead_detail['call_attempts_count']}")
                print(f"  Secuencia outcomes: {outcomes_seq}")

                # Aplicar reglas
                if outcomes_seq:
                    outcomes_list = [int(o) for o in outcomes_seq.split(',') if o != 'None']
                    count_6 = outcomes_list.count(6)

                    if count_6 >= 2:
                        print(f"  → DEBE SER: Numero erroneo (tiene {count_6} outcomes 6)")
                    elif count_6 == 1:
                        print(f"  → DEBE SER: Volver a llamar (tiene 1 outcome 6)")
                    elif all(o in [4, 5, 7] for o in outcomes_list):
                        if lead_detail['call_attempts_count'] >= 6:
                            print(f"  → DEBE SER: No Interesado (max intentos, solo no-contacto)")
                        else:
                            print(f"  → DEBE SER: Volver a llamar (solo no-contacto)")
                    else:
                        print(f"  → REVISAR: Outcomes no estándar: {set(outcomes_list)}")
                else:
                    print(f"  → REVISAR: Sin outcomes")

    except Exception as e:
        logger.error(f"Error en análisis: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    simple_outcomes_analysis()
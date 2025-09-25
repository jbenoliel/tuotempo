#!/usr/bin/env python3
"""
Script para analizar en detalle los "otros estados" y determinar si tienen llamadas
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

def analizar_otros_estados():
    """Analizar en detalle los otros estados y sus llamadas"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== ANÁLISIS DETALLADO DE 'OTROS ESTADOS' ===")

            # 1. Obtener todos los leads en "otros estados"
            cursor.execute("""
                SELECT
                    id, nombre, apellidos, telefono,
                    status_level_1, status_level_2,
                    call_attempts_count, lead_status,
                    call_status, selected_for_calling,
                    last_call_attempt
                FROM leads
                WHERE
                    TRIM(status_level_1) IN ('Numero erroneo', 'Interesado')
                    OR status_level_1 IS NULL
                    OR TRIM(status_level_1) = ''
                    OR TRIM(status_level_1) = 'None'
                ORDER BY status_level_1, call_attempts_count DESC
            """)

            otros_leads = cursor.fetchall()
            print(f"\n1. TOTAL DE LEADS EN 'OTROS ESTADOS': {len(otros_leads)}")

            # 2. Análisis por tipo de "otro estado"
            estados_breakdown = {}
            for lead in otros_leads:
                status = lead['status_level_1']
                if status is None or status.strip() == '' or status.strip() == 'None':
                    key = 'NULL/VACÍO/None'
                else:
                    key = status.strip()

                if key not in estados_breakdown:
                    estados_breakdown[key] = []
                estados_breakdown[key].append(lead)

            print(f"\n2. DESGLOSE POR TIPO DE ESTADO:")
            for estado, leads_list in estados_breakdown.items():
                print(f"\n   {estado}: {len(leads_list)} leads")

                # Estadísticas de llamadas para este estado
                con_llamadas = sum(1 for l in leads_list if l['call_attempts_count'] and l['call_attempts_count'] > 0)
                sin_llamadas = len(leads_list) - con_llamadas

                print(f"     Con llamadas: {con_llamadas}")
                print(f"     Sin llamadas: {sin_llamadas}")

                if con_llamadas > 0:
                    intentos_promedio = sum(l['call_attempts_count'] or 0 for l in leads_list) / len(leads_list)
                    max_intentos = max(l['call_attempts_count'] or 0 for l in leads_list)
                    print(f"     Intentos promedio: {intentos_promedio:.1f}")
                    print(f"     Máx intentos: {max_intentos}")

                # Análisis de lead_status (abierto/cerrado)
                abiertos = sum(1 for l in leads_list if l['lead_status'] == 'open')
                cerrados = sum(1 for l in leads_list if l['lead_status'] == 'closed')
                print(f"     Abiertos: {abiertos} | Cerrados: {cerrados}")

                # Mostrar algunos ejemplos
                if len(leads_list) <= 10:
                    print(f"     EJEMPLOS:")
                    for lead in leads_list[:10]:
                        print(f"       ID {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                        print(f"         Status L1/L2: '{lead['status_level_1']}'/ '{lead['status_level_2']}'")
                        print(f"         Intentos: {lead['call_attempts_count']} | Lead: {lead['lead_status']} | Call: {lead['call_status']}")
                        if lead['last_call_attempt']:
                            print(f"         Última llamada: {lead['last_call_attempt']}")
                        print("         ---")

            # 3. Análisis específico de los que tienen llamadas realizadas
            print(f"\n3. ANÁLISIS DE LEADS CON LLAMADAS REALIZADAS:")

            leads_con_llamadas = [l for l in otros_leads if l['call_attempts_count'] and l['call_attempts_count'] > 0]
            print(f"   Total con llamadas: {len(leads_con_llamadas)}")

            if leads_con_llamadas:
                # Buscar llamadas en pearl_calls para estos leads
                lead_ids = [str(l['id']) for l in leads_con_llamadas]

                if lead_ids:
                    placeholders = ','.join(['%s'] * len(lead_ids))
                    cursor.execute(f"""
                        SELECT
                            pc.lead_id,
                            COUNT(*) as total_llamadas,
                            GROUP_CONCAT(DISTINCT pc.outcome ORDER BY pc.call_time DESC) as outcomes,
                            MAX(pc.call_time) as ultima_llamada_pearl
                        FROM pearl_calls pc
                        WHERE pc.lead_id IN ({placeholders})
                        GROUP BY pc.lead_id
                        ORDER BY total_llamadas DESC
                    """, lead_ids)

                    pearl_data = cursor.fetchall()

                    print(f"\n   Leads con registro en pearl_calls: {len(pearl_data)}")

                    if pearl_data:
                        print(f"   DETALLES DE LLAMADAS EN PEARL_CALLS:")
                        for pearl in pearl_data[:10]:  # Mostrar los primeros 10
                            # Encontrar el lead correspondiente
                            lead_data = next((l for l in leads_con_llamadas if l['id'] == pearl['lead_id']), None)
                            if lead_data:
                                print(f"     Lead {pearl['lead_id']}: {lead_data['nombre']} {lead_data['apellidos']}")
                                print(f"       Status: '{lead_data['status_level_1']}' / '{lead_data['status_level_2']}'")
                                print(f"       Call attempts: {lead_data['call_attempts_count']}")
                                print(f"       Pearl calls: {pearl['total_llamadas']}")
                                print(f"       Outcomes: {pearl['outcomes']}")
                                print(f"       Última en Pearl: {pearl['ultima_llamada_pearl']}")
                                print("       ---")

            # 4. Recomendación sobre qué hacer con estos estados
            print(f"\n4. RECOMENDACIONES:")

            for estado, leads_list in estados_breakdown.items():
                con_llamadas = sum(1 for l in leads_list if l['call_attempts_count'] and l['call_attempts_count'] > 0)
                sin_llamadas = len(leads_list) - con_llamadas
                cerrados = sum(1 for l in leads_list if l['lead_status'] == 'closed')

                print(f"\n   {estado} ({len(leads_list)} leads):")

                if estado == 'Interesado':
                    print(f"     → ACCIÓN: Revisar y reclasificar. Podrían ser 'Volver a llamar' o 'Útiles Positivos'")
                elif estado == 'Numero erroneo':
                    print(f"     → ACCIÓN: Si no tienen más números alternativos, cerrar como 'No contactable'")
                elif estado == 'NULL/VACÍO/None':
                    if cerrados > 0:
                        print(f"     → {cerrados} están cerrados: Probablemente ya procesados, verificar si necesitan reclasificación")
                    if sin_llamadas > 0:
                        print(f"     → {sin_llamadas} sin llamadas: Leads nuevos pendientes de procesar")
                    if con_llamadas > 0:
                        print(f"     → {con_llamadas} con llamadas pero sin status: REVISAR - posible error de clasificación")

    except Exception as e:
        logger.error(f"Error en análisis: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analizar_otros_estados()
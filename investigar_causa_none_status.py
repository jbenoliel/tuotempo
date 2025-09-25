#!/usr/bin/env python3
"""
Script para investigar la causa raíz de por qué aparecen leads con status_level_1 = 'None'
e incluir summary de llamadas para entender qué pasó
"""

import pymysql
import pandas as pd
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

def investigar_causa_none_status():
    """Investigar por qué aparecen leads con status_level_1 = 'None'"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== INVESTIGACIÓN CAUSA RAÍZ DE STATUS_LEVEL_1 = 'None' ===")

            # 1. Análisis temporal: ¿cuándo aparecieron estos leads?
            cursor.execute("""
                SELECT
                    MIN(last_call_attempt) as primera_llamada,
                    MAX(last_call_attempt) as ultima_llamada,
                    COUNT(*) as total
                FROM leads
                WHERE status_level_1 = 'None'
            """)
            temporal = cursor.fetchone()
            print(f"\n1. ANÁLISIS TEMPORAL:")
            print(f"   Leads con status 'None': {temporal['total']}")
            print(f"   Primera llamada: {temporal['primera_llamada']}")
            print(f"   Última llamada: {temporal['ultima_llamada']}")

            # 2. ¿Hay algún patrón en los IDs?
            cursor.execute("""
                SELECT MIN(id) as min_id, MAX(id) as max_id
                FROM leads
                WHERE status_level_1 = 'None'
            """)
            ids_pattern = cursor.fetchone()
            print(f"\n2. PATRÓN DE IDs:")
            print(f"   Rango de IDs: {ids_pattern['min_id']} - {ids_pattern['max_id']}")

            # 3. Comparar con leads normales del mismo periodo
            cursor.execute("""
                SELECT
                    status_level_1,
                    COUNT(*) as count
                FROM leads
                WHERE id BETWEEN %s AND %s
                GROUP BY status_level_1
                ORDER BY count DESC
            """, (ids_pattern['min_id'], ids_pattern['max_id']))

            status_pattern = cursor.fetchall()
            print(f"\n3. STATUS EN EL MISMO RANGO DE IDs ({ids_pattern['min_id']}-{ids_pattern['max_id']}):")
            for status in status_pattern:
                print(f"   '{status['status_level_1']}': {status['count']} leads")

            # 4. Obtener detalles completos incluyendo call_summary si existe
            print(f"\n4. GENERANDO EXCEL CON DETALLES COMPLETOS...")

            cursor.execute("""
                SELECT
                    l.id, l.nombre, l.apellidos, l.telefono, l.telefono2,
                    l.status_level_1, l.status_level_2,
                    l.call_attempts_count, l.lead_status,
                    l.call_status, l.selected_for_calling,
                    l.last_call_attempt, l.closure_reason,
                    l.origen_archivo
                FROM leads l
                WHERE l.status_level_1 = 'None'
                ORDER BY l.id
            """)

            leads_none = cursor.fetchall()

            # 5. Para cada lead, obtener TODAS sus llamadas con detalles
            leads_detallados = []

            for lead in leads_none:
                lead_id = lead['id']

                # Obtener todas las llamadas de pearl_calls
                cursor.execute("""
                    SELECT
                        call_time,
                        outcome
                    FROM pearl_calls
                    WHERE lead_id = %s
                    ORDER BY call_time ASC
                """, (lead_id,))

                llamadas = cursor.fetchall()

                # Construir timeline de llamadas
                timeline_llamadas = []
                outcomes_list = []

                for i, llamada in enumerate(llamadas):
                    outcome_texto = ""
                    if llamada['outcome'] == 4:
                        outcome_texto = "Ocupado"
                    elif llamada['outcome'] == 5:
                        outcome_texto = "Colgó"
                    elif llamada['outcome'] == 6:
                        outcome_texto = "Outcome_6"
                    elif llamada['outcome'] == 7:
                        outcome_texto = "No_contesta"
                    elif llamada['outcome'] is None:
                        outcome_texto = "Sin_outcome"
                    else:
                        outcome_texto = f"Outcome_{llamada['outcome']}"

                    outcomes_list.append(outcome_texto)
                    timeline_llamadas.append(f"[{i+1}] {llamada['call_time']} -> {outcome_texto}")

                # Buscar si hay algún registro en otras tablas que podría explicar el 'None'
                # (Por ejemplo, alguna tabla de log o auditoría)

                # Determinar qué debería ser el status correcto
                status_sugerido = "INDETERMINADO"
                if outcomes_list:
                    # Si todos los outcomes son de "no contacto" (4,5,7) y no alcanzó máx intentos
                    if all(o in ["Ocupado", "Colgó", "No_contesta"] for o in outcomes_list if o != "Sin_outcome"):
                        if lead['call_attempts_count'] >= 6:
                            status_sugerido = "NO_UTIL_MAX_INTENTOS"
                        else:
                            status_sugerido = "VOLVER_A_LLAMAR"
                    elif "Outcome_6" in outcomes_list:
                        status_sugerido = "REVISAR_OUTCOME_6"
                    else:
                        status_sugerido = "REVISAR_OUTCOMES_MIXTOS"

                # Detectar posibles causas
                causas_posibles = []
                if lead['lead_status'] == 'closed':
                    causas_posibles.append("Lead_cerrado_automaticamente")
                if not outcomes_list:
                    causas_posibles.append("Sin_llamadas_registradas")
                if len(set(outcomes_list)) == 1 and outcomes_list[0] in ["Ocupado", "Colgó", "No_contesta"]:
                    causas_posibles.append("Todas_llamadas_mismo_outcome_negativo")
                if lead['call_attempts_count'] != len(llamadas):
                    causas_posibles.append(f"Discrepancia_intentos_vs_llamadas_{lead['call_attempts_count']}_vs_{len(llamadas)}")

                lead_detallado = {
                    'ID': lead['id'],
                    'Nombre': lead['nombre'],
                    'Apellidos': lead['apellidos'],
                    'Telefono': lead['telefono'],
                    'Telefono2': lead['telefono2'],
                    'Status_L1': lead['status_level_1'],
                    'Status_L2': lead['status_level_2'],
                    'Call_Attempts': lead['call_attempts_count'],
                    'Lead_Status': lead['lead_status'],
                    'Call_Status': lead['call_status'],
                    'Selected': lead['selected_for_calling'],
                    'Last_Call_Attempt': lead['last_call_attempt'],
                    'Closure_Reason': lead['closure_reason'],
                    'Origen_Archivo': lead['origen_archivo'],
                    'Total_Pearl_Calls': len(llamadas),
                    'Outcomes_Lista': " -> ".join(outcomes_list),
                    'Timeline_Completo': " | ".join(timeline_llamadas),
                    'Status_Sugerido': status_sugerido,
                    'Causas_Posibles': " | ".join(causas_posibles)
                }

                leads_detallados.append(lead_detallado)

            # 6. Crear Excel mejorado
            df = pd.DataFrame(leads_detallados)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_excel = f"leads_none_investigacion_{timestamp}.xlsx"

            with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Investigacion_None_Status', index=False)

                worksheet = writer.sheets['Investigacion_None_Status']

                # Ajustar columnas
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 80)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            print(f"Excel investigación generado: {archivo_excel}")

            # 7. Análisis de patrones
            print(f"\n5. ANÁLISIS DE PATRONES ENCONTRADOS:")

            causas_contador = {}
            status_sugerido_contador = {}

            for lead in leads_detallados:
                # Contar causas
                for causa in lead['Causas_Posibles'].split(' | '):
                    if causa:
                        causas_contador[causa] = causas_contador.get(causa, 0) + 1

                # Contar status sugeridos
                status = lead['Status_Sugerido']
                status_sugerido_contador[status] = status_sugerido_contador.get(status, 0) + 1

            print(f"\n   CAUSAS IDENTIFICADAS:")
            for causa, count in sorted(causas_contador.items(), key=lambda x: x[1], reverse=True):
                print(f"     {causa}: {count} leads")

            print(f"\n   STATUS SUGERIDOS:")
            for status, count in sorted(status_sugerido_contador.items(), key=lambda x: x[1], reverse=True):
                print(f"     {status}: {count} leads")

            # 8. Recomendaciones para prevenir el problema
            print(f"\n6. RECOMENDACIONES PARA PREVENIR EL PROBLEMA:")
            print(f"   a) Verificar el código que procesa outcomes de llamadas")
            print(f"   b) Asegurar que siempre se asigne un status_level_1 válido")
            print(f"   c) Implementar validación que evite status = 'None'")
            print(f"   d) Revisar el proceso de cierre automático de leads")

            return archivo_excel

    except Exception as e:
        logger.error(f"Error en investigación: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    archivo = investigar_causa_none_status()
    if archivo:
        print(f"\nInvestigación completada. Excel generado: {archivo}")
    else:
        print("Error en la investigación")
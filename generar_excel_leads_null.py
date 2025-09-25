#!/usr/bin/env python3
"""
Script para generar Excel con los 31 leads NULL/VACÍO/None y sus detalles completos de llamadas
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

def generar_excel_leads_null():
    """Generar Excel con detalles completos de los leads NULL/VACÍO/None"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== GENERANDO EXCEL CON LEADS NULL/VACÍO/None ===")

            # 1. Obtener los leads NULL/VACÍO/None
            cursor.execute("""
                SELECT
                    id, nombre, apellidos, telefono, telefono2,
                    status_level_1, status_level_2,
                    call_attempts_count, lead_status,
                    call_status, selected_for_calling,
                    last_call_attempt,
                    closure_reason
                FROM leads
                WHERE
                    status_level_1 IS NULL
                    OR TRIM(status_level_1) = ''
                    OR TRIM(status_level_1) = 'None'
                ORDER BY id
            """)

            leads_null = cursor.fetchall()
            print(f"Encontrados {len(leads_null)} leads NULL/VACÍO/None")

            # 2. Para cada lead, obtener el detalle de sus llamadas de pearl_calls
            leads_con_detalles = []

            for lead in leads_null:
                lead_id = lead['id']

                # Obtener llamadas de pearl_calls
                cursor.execute("""
                    SELECT
                        call_time,
                        outcome
                    FROM pearl_calls
                    WHERE lead_id = %s
                    ORDER BY call_time DESC
                    LIMIT 10
                """, (lead_id,))

                llamadas = cursor.fetchall()

                # Preparar el resumen de llamadas
                if llamadas:
                    ultima_llamada = llamadas[0]
                    todas_llamadas = []
                    outcomes_unicos = set()

                    for llamada in llamadas:
                        outcome_texto = ""
                        if llamada['outcome'] == 4:
                            outcome_texto = "Ocupado"
                        elif llamada['outcome'] == 5:
                            outcome_texto = "Colgó"
                        elif llamada['outcome'] == 7:
                            outcome_texto = "No contesta"
                        elif llamada['outcome'] is None:
                            outcome_texto = "Sin outcome"
                        else:
                            outcome_texto = f"Outcome {llamada['outcome']}"

                        outcomes_unicos.add(outcome_texto)

                        llamada_str = f"{llamada['call_time']} - {outcome_texto}"
                        todas_llamadas.append(llamada_str)

                    resumen_llamadas = " | ".join(todas_llamadas)
                    outcomes_resumen = ", ".join(sorted(outcomes_unicos))

                    # Determinar categoría sugerida basada en outcomes
                    if any(outcome in ["4", "5", "7"] for outcome in [str(llamada['outcome']) for llamada in llamadas if llamada['outcome']]):
                        if lead['call_attempts_count'] >= 6:
                            categoria_sugerida = "No Útil (máx intentos)"
                        else:
                            categoria_sugerida = "Volver a llamar"
                    else:
                        categoria_sugerida = "Revisar manualmente"

                else:
                    resumen_llamadas = "Sin llamadas en pearl_calls"
                    outcomes_resumen = ""
                    categoria_sugerida = "Sin datos de llamadas"

                # Agregar al resultado
                lead_detalle = {
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
                    'Total_Pearl_Calls': len(llamadas),
                    'Outcomes_Resumen': outcomes_resumen,
                    'Categoria_Sugerida': categoria_sugerida,
                    'Detalle_Completo_Llamadas': resumen_llamadas
                }

                leads_con_detalles.append(lead_detalle)

            # 3. Crear DataFrame y exportar a Excel
            df = pd.DataFrame(leads_con_detalles)

            # Generar nombre del archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_excel = f"leads_null_detalle_{timestamp}.xlsx"

            # Crear el Excel con formato
            with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Leads_NULL_Detalle', index=False)

                # Obtener el worksheet para formato
                worksheet = writer.sheets['Leads_NULL_Detalle']

                # Ajustar ancho de columnas
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            print(f"Excel generado: {archivo_excel}")

            # 4. Mostrar resumen en consola
            print(f"\n=== RESUMEN DE LEADS NULL/VACÍO/None ===")
            print(f"Total leads: {len(leads_con_detalles)}")

            categorias_sugeridas = {}
            for lead in leads_con_detalles:
                cat = lead['Categoria_Sugerida']
                categorias_sugeridas[cat] = categorias_sugeridas.get(cat, 0) + 1

            print(f"\nCategorías sugeridas:")
            for categoria, count in sorted(categorias_sugeridas.items()):
                print(f"  {categoria}: {count} leads")

            # 5. Análisis de outcomes
            outcomes_contador = {}
            for lead in leads_con_detalles:
                outcomes = lead['Outcomes_Resumen']
                if outcomes:
                    for outcome in outcomes.split(', '):
                        outcomes_contador[outcome] = outcomes_contador.get(outcome, 0) + 1

            print(f"\nOutcomes encontrados:")
            for outcome, count in sorted(outcomes_contador.items()):
                print(f"  {outcome}: {count} leads")

            print(f"\nArchivo Excel generado: {archivo_excel}")
            return archivo_excel

    except Exception as e:
        logger.error(f"Error generando Excel: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    archivo = generar_excel_leads_null()
    if archivo:
        print(f"Excel generado exitosamente: {archivo}")
    else:
        print("Error al generar Excel")
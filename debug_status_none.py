#!/usr/bin/env python3
"""
Script para debuggear exactamente cómo están los status_level_1 de los leads huérfanos
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

def debug_status_none():
    """Debug exacto de los status de los 31 leads huérfanos"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== DEBUG EXACTO DE STATUS_LEVEL_1 DE LEADS HUÉRFANOS ===")

            # Usar los IDs exactos que encontramos antes
            leads_huerfanos_ids = [1971, 1985, 1989, 2000, 2002, 2005, 2072, 2090, 2092, 2094, 2098, 2108, 2132, 2147, 2157, 2162, 2186, 2243, 2261, 2264, 2273, 2280, 2315, 2323, 2328, 2372, 2388, 2399, 2405, 2407, 2422]

            placeholders = ','.join(['%s'] * len(leads_huerfanos_ids))

            # 1. Ver exactamente qué contienen sus campos status_level_1
            cursor.execute(f"""
                SELECT
                    id, nombre, apellidos,
                    status_level_1,
                    status_level_2,
                    LENGTH(status_level_1) as length_status1,
                    HEX(status_level_1) as hex_status1,
                    ASCII(status_level_1) as ascii_status1,
                    call_attempts_count,
                    lead_status,
                    last_call_attempt,
                    origen_archivo
                FROM leads
                WHERE id IN ({placeholders})
                ORDER BY id
            """, leads_huerfanos_ids)

            leads_debug = cursor.fetchall()

            print(f"\n1. ANÁLISIS EXACTO DE STATUS_LEVEL_1:")
            valores_unicos = set()

            for lead in leads_debug:
                valor = lead['status_level_1']
                length = lead['length_status1']
                hex_val = lead['hex_status1']
                ascii_val = lead['ascii_status1']

                valores_unicos.add((valor, length, hex_val))

                print(f"ID {lead['id']}: '{valor}' (len={length}, hex={hex_val}, ascii={ascii_val})")

            print(f"\n2. VALORES ÚNICOS ENCONTRADOS:")
            for valor, length, hex_val in valores_unicos:
                print(f"   Valor: '{valor}' | Length: {length} | Hex: {hex_val}")

            # 2. Ahora obtener el detalle completo de llamadas para Excel
            leads_completos = []

            for lead in leads_debug:
                lead_id = lead['id']

                # Obtener llamadas de pearl_calls
                cursor.execute("""
                    SELECT
                        call_time,
                        outcome
                    FROM pearl_calls
                    WHERE lead_id = %s
                    ORDER BY call_time ASC
                """, (lead_id,))

                llamadas = cursor.fetchall()

                # Procesar outcomes
                outcomes_timeline = []
                outcomes_resumen = []

                for llamada in llamadas:
                    outcome = llamada['outcome']
                    outcome_texto = ""

                    if outcome == 4:
                        outcome_texto = "Ocupado"
                    elif outcome == 5:
                        outcome_texto = "Colgó"
                    elif outcome == 6:
                        outcome_texto = "Outcome_6"  # Necesitamos saber qué es esto
                    elif outcome == 7:
                        outcome_texto = "No_contesta"
                    elif outcome is None:
                        outcome_texto = "Sin_outcome"
                    else:
                        outcome_texto = f"Outcome_{outcome}"

                    outcomes_resumen.append(outcome_texto)
                    outcomes_timeline.append(f"{llamada['call_time']} -> {outcome_texto}")

                # Análisis del patrón
                patron_outcome = "MIXTO"
                if not outcomes_resumen:
                    patron_outcome = "SIN_LLAMADAS"
                elif all(o == outcomes_resumen[0] for o in outcomes_resumen):
                    patron_outcome = f"TODOS_{outcomes_resumen[0]}"
                elif all(o in ["Ocupado", "Colgó", "No_contesta"] for o in outcomes_resumen):
                    patron_outcome = "TODOS_NO_CONTACTO"

                # Determinar qué debería ser el status
                status_correcto = "INDETERMINADO"
                if lead['call_attempts_count'] >= 6:
                    status_correcto = "No Interesado (max intentos)"
                elif patron_outcome == "TODOS_NO_CONTACTO":
                    status_correcto = "Volver a llamar"
                elif "Outcome_6" in outcomes_resumen:
                    status_correcto = "Revisar Outcome_6"

                lead_completo = {
                    'ID': lead['id'],
                    'Nombre': lead['nombre'],
                    'Apellidos': lead['apellidos'],
                    'Status_L1_Actual': lead['status_level_1'],
                    'Status_L1_Length': lead['length_status1'],
                    'Status_L1_Hex': lead['hex_status1'],
                    'Status_L2': lead['status_level_2'],
                    'Call_Attempts': lead['call_attempts_count'],
                    'Lead_Status': lead['lead_status'],
                    'Last_Call': lead['last_call_attempt'],
                    'Origen_Archivo': lead['origen_archivo'],
                    'Total_Pearl_Calls': len(llamadas),
                    'Patron_Outcomes': patron_outcome,
                    'Outcomes_Secuencia': " -> ".join(outcomes_resumen),
                    'Timeline_Completo': " | ".join(outcomes_timeline),
                    'Status_Correcto_Sugerido': status_correcto
                }

                leads_completos.append(lead_completo)

            # 3. Generar Excel mejorado
            df = pd.DataFrame(leads_completos)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_excel = f"debug_leads_huerfanos_completo_{timestamp}.xlsx"

            with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Debug_Leads_Huerfanos', index=False)

                worksheet = writer.sheets['Debug_Leads_Huerfanos']

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
                    adjusted_width = min(max_length + 2, 100)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            print(f"\n3. Excel completo generado: {archivo_excel}")

            # 4. Estadísticas finales
            patrones = {}
            status_sugeridos = {}

            for lead in leads_completos:
                patron = lead['Patron_Outcomes']
                status = lead['Status_Correcto_Sugerido']

                patrones[patron] = patrones.get(patron, 0) + 1
                status_sugeridos[status] = status_sugeridos.get(status, 0) + 1

            print(f"\n4. ESTADÍSTICAS FINALES:")
            print(f"   PATRONES DE OUTCOMES:")
            for patron, count in sorted(patrones.items()):
                print(f"     {patron}: {count} leads")

            print(f"\n   STATUS CORRECTOS SUGERIDOS:")
            for status, count in sorted(status_sugeridos.items()):
                print(f"     {status}: {count} leads")

            return archivo_excel

    except Exception as e:
        logger.error(f"Error en debug: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    archivo = debug_status_none()
    if archivo:
        print(f"\nDebug completado. Archivo: {archivo}")
    else:
        print("Error en debug")
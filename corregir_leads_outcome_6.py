#!/usr/bin/env python3
"""
Script para analizar y corregir los leads con Outcome 6 (Failed)
Regla: 1 vez = Volver a llamar, 2+ veces = Número erróneo
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

def corregir_leads_outcome_6():
    """Analizar y proponer correcciones para leads con Outcome 6 (Failed)"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== ANÁLISIS Y CORRECCIÓN DE LEADS CON OUTCOME 6 (FAILED) ===")

            # IDs de los leads huérfanos
            leads_huerfanos_ids = [1971, 1985, 1989, 2000, 2002, 2005, 2072, 2090, 2092, 2094, 2098, 2108, 2132, 2147, 2157, 2162, 2186, 2243, 2261, 2264, 2273, 2280, 2315, 2323, 2328, 2372, 2388, 2399, 2405, 2407, 2422]

            leads_para_corregir = []

            for lead_id in leads_huerfanos_ids:
                # Obtener info del lead
                cursor.execute("""
                    SELECT
                        id, nombre, apellidos, telefono,
                        status_level_1, status_level_2,
                        call_attempts_count, lead_status,
                        last_call_attempt
                    FROM leads
                    WHERE id = %s
                """, (lead_id,))

                lead = cursor.fetchone()
                if not lead:
                    continue

                # Obtener todas sus llamadas con outcomes
                cursor.execute("""
                    SELECT
                        call_time,
                        outcome
                    FROM pearl_calls
                    WHERE lead_id = %s
                    ORDER BY call_time ASC
                """, (lead_id,))

                llamadas = cursor.fetchall()

                # Analizar patrones de outcomes
                outcomes = [llamada['outcome'] for llamada in llamadas if llamada['outcome'] is not None]
                outcome_6_count = outcomes.count(6)
                total_llamadas = len(outcomes)

                # Determinar status correcto según reglas de negocio
                status_sugerido = "INDETERMINADO"
                razon = ""

                if outcome_6_count >= 2:
                    # REGLA: 2+ outcomes 6 = Número erróneo
                    status_sugerido = "Numero erroneo"
                    razon = f"Outcome 6 (Failed) repetido {outcome_6_count} veces = número erróneo"
                elif outcome_6_count == 1:
                    # REGLA: 1 outcome 6 = Problema temporal centralita = Volver a llamar
                    status_sugerido = "Volver a llamar"
                    razon = "1 outcome 6 (Failed) = problema temporal centralita"
                elif outcome_6_count == 0:
                    # No tiene outcome 6, analizar otros outcomes
                    if not outcomes:
                        status_sugerido = "REVISAR_MANUALMENTE"
                        razon = "Sin outcomes en pearl_calls"
                    elif all(o in [4, 5, 7] for o in outcomes):
                        # Solo outcomes de no-contacto (4=ocupado, 5=colgó, 7=no contesta)
                        if lead['call_attempts_count'] >= 6:
                            status_sugerido = "No Interesado"
                            razon = "Máximo intentos alcanzado - solo no-contacto"
                        else:
                            status_sugerido = "Volver a llamar"
                            razon = "Solo outcomes de no-contacto"
                    else:
                        # Tiene otros outcomes desconocidos
                        outcomes_unicos = list(set(outcomes))
                        status_sugerido = "REVISAR_MANUALMENTE"
                        razon = f"Outcomes desconocidos: {outcomes_unicos}"

                # Determinar status_level_2 apropiado
                status_level_2 = ""
                if status_sugerido == "Numero erroneo":
                    status_level_2 = "Falló multiple veces"
                elif status_sugerido == "Volver a llamar":
                    if outcome_6_count > 0:
                        status_level_2 = "Fallo centralita"
                    else:
                        # Buscar el outcome más común
                        if 4 in outcomes:
                            status_level_2 = "no disponible cliente"
                        elif 5 in outcomes:
                            status_level_2 = "cortado"
                        elif 7 in outcomes:
                            status_level_2 = "buzón"
                        else:
                            status_level_2 = "no disponible cliente"

                lead_correccion = {
                    'ID': lead['id'],
                    'Nombre': lead['nombre'],
                    'Apellidos': lead['apellidos'],
                    'Telefono': lead['telefono'],
                    'Status_Actual_L1': lead['status_level_1'],
                    'Status_Actual_L2': lead['status_level_2'],
                    'Call_Attempts': lead['call_attempts_count'],
                    'Lead_Status': lead['lead_status'],
                    'Total_Llamadas': total_llamadas,
                    'Outcome_6_Count': outcome_6_count,
                    'Todos_Outcomes': str(outcomes),
                    'Status_Nuevo_L1': status_sugerido,
                    'Status_Nuevo_L2': status_level_2,
                    'Razon_Correccion': razon,
                    'Accion': 'UPDATE' if status_sugerido not in ['INDETERMINADO', 'REVISAR_MANUALMENTE'] else 'REVISAR'
                }

                leads_para_corregir.append(lead_correccion)

            # Generar Excel con análisis
            df = pd.DataFrame(leads_para_corregir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_excel = f"correccion_leads_outcome6_{timestamp}.xlsx"

            with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Correcciones_Propuestas', index=False)

                worksheet = writer.sheets['Correcciones_Propuestas']

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

            print(f"Excel con correcciones generado: {archivo_excel}")

            # Mostrar estadísticas
            stats = {}
            acciones = {}

            for lead in leads_para_corregir:
                status = lead['Status_Nuevo_L1']
                accion = lead['Accion']

                stats[status] = stats.get(status, 0) + 1
                acciones[accion] = acciones.get(accion, 0) + 1

            print(f"\n=== ESTADÍSTICAS DE CORRECCIONES PROPUESTAS ===")
            print(f"STATUS PROPUESTOS:")
            for status, count in sorted(stats.items()):
                print(f"  {status}: {count} leads")

            print(f"\nACCIONES:")
            for accion, count in sorted(acciones.items()):
                print(f"  {accion}: {count} leads")

            # Generar SQL para aplicar correcciones automáticas
            updates_sql = []
            leads_update = [l for l in leads_para_corregir if l['Accion'] == 'UPDATE']

            if leads_update:
                print(f"\n=== SQL PARA APLICAR CORRECCIONES AUTOMÁTICAS ({len(leads_update)} leads) ===")

                for lead in leads_update:
                    sql = f"""UPDATE leads SET
                        status_level_1 = '{lead['Status_Nuevo_L1']}',
                        status_level_2 = '{lead['Status_Nuevo_L2']}'
                        WHERE id = {lead['ID']};
                    """
                    updates_sql.append(sql)
                    print(sql.strip())

                # Guardar SQL en archivo
                sql_file = f"correccion_leads_outcome6_{timestamp}.sql"
                with open(sql_file, 'w', encoding='utf-8') as f:
                    f.write("-- Correcciones automáticas para leads con Outcome 6 (Failed)\n")
                    f.write("-- Generado automáticamente el " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                    for sql in updates_sql:
                        f.write(sql + "\n")

                print(f"\nSQL guardado en: {sql_file}")

            return archivo_excel, len(leads_update)

    except Exception as e:
        logger.error(f"Error en corrección: {e}")
        return None, 0
    finally:
        conn.close()

if __name__ == "__main__":
    archivo, updates_count = corregir_leads_outcome_6()
    if archivo:
        print(f"\nAnálisis completado.")
        print(f"Excel: {archivo}")
        print(f"Updates automáticos propuestos: {updates_count}")
    else:
        print("Error en el análisis")
"""
Script para actualizar campos call_id, call_summary, call_time y call_duration
basándose en la información del Excel "Total llamadas.xlsx"
Se toma la llamada más reciente para cada teléfono.
"""

import os
import pandas as pd
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import re

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Crear conexión a la base de datos Railway"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQLHOST'),
            port=int(os.getenv('MYSQLPORT')),
            user=os.getenv('MYSQLUSER'),
            password=os.getenv('MYSQLPASSWORD'),
            database=os.getenv('MYSQLDATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

def limpiar_telefono(telefono):
    """Limpia el número de teléfono removiendo el código de país y caracteres no numéricos"""
    if pd.isna(telefono):
        return None

    telefono_str = str(telefono)
    telefono_limpio = re.sub(r'[^0-9]', '', telefono_str)

    # Remover código de país 34 si está presente
    if telefono_limpio.startswith('34') and len(telefono_limpio) > 9:
        telefono_limpio = telefono_limpio[2:]

    # Validar que tenga 9 dígitos
    if len(telefono_limpio) == 9:
        return telefono_limpio

    return None

def procesar_excel_llamadas():
    """Procesa el Excel y extrae la información más reciente por teléfono"""

    excel_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\Total llamadas.xlsx"

    print(f"Procesando archivo Excel: {excel_path}")

    try:
        # Leer el Excel
        df = pd.read_excel(excel_path)
        print(f"Registros leídos: {len(df)}")
        print(f"Columnas: {list(df.columns)}")

        # Limpiar teléfonos
        df['telefono_limpio'] = df['To'].apply(limpiar_telefono)
        df_validos = df[df['telefono_limpio'].notna()].copy()

        print(f"Registros con teléfonos válidos: {len(df_validos)}")

        # Convertir StartTime a datetime
        df_validos['StartTime'] = pd.to_datetime(df_validos['StartTime'])

        # Obtener la llamada más reciente por teléfono
        df_mas_reciente = df_validos.loc[df_validos.groupby('telefono_limpio')['StartTime'].idxmax()]

        print(f"Teléfonos únicos con llamada más reciente: {len(df_mas_reciente)}")

        # Crear diccionario con la información
        info_llamadas = {}

        for _, row in df_mas_reciente.iterrows():
            telefono = row['telefono_limpio']
            info_llamadas[telefono] = {
                'call_id': str(row['Id']) if pd.notna(row['Id']) else None,
                'call_time': row['StartTime'] if pd.notna(row['StartTime']) else None,
                'call_summary': str(row['Summary']) if pd.notna(row['Summary']) and str(row['Summary']).strip() not in ['nan', '', 'None'] else None,
                'call_duration': int(row['Duration']) if pd.notna(row['Duration']) and str(row['Duration']).replace('.', '').isdigit() else None,
                'conversation_status': str(row['ConversationStatus']) if pd.notna(row['ConversationStatus']) else None,
                'status': str(row['Status']) if pd.notna(row['Status']) else None
            }

        print(f"\nEjemplos de información extraída:")
        count = 0
        for telefono, info in info_llamadas.items():
            if count < 5:
                print(f"  {telefono}: ID={info['call_id']}, Time={info['call_time']}, Status={info['conversation_status']}")
                print(f"    Summary: {info['call_summary'][:100] if info['call_summary'] else 'None'}...")
                count += 1

        return info_llamadas

    except Exception as e:
        print(f"Error procesando Excel: {e}")
        return None

def actualizar_campos_llamada(info_llamadas):
    """Actualiza los campos de llamada en la tabla leads"""

    if not info_llamadas:
        print("No hay información de llamadas para procesar")
        return

    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            print("\n=== ACTUALIZANDO CAMPOS DE LLAMADA DESDE EXCEL ===")

            leads_actualizados = 0
            leads_sin_match = 0
            campos_actualizados = {
                'call_id': 0,
                'call_time': 0,
                'call_summary': 0,
                'call_duration': 0
            }

            print("Procesando leads...")

            for telefono, info in info_llamadas.items():
                # Buscar leads que coincidan con este teléfono
                cursor.execute("""
                    SELECT id, nombre, call_id, call_summary, call_time, call_duration
                    FROM leads
                    WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s
                """, (telefono,))

                leads_coincidentes = cursor.fetchall()

                if leads_coincidentes:
                    for lead in leads_coincidentes:
                        # Preparar campos a actualizar
                        campos_update = []
                        valores_update = []

                        # call_id
                        if info['call_id'] and (not lead['call_id'] or lead['call_id'].strip() == ''):
                            campos_update.append("call_id = %s")
                            valores_update.append(info['call_id'])
                            campos_actualizados['call_id'] += 1

                        # call_time
                        if info['call_time'] and not lead['call_time']:
                            campos_update.append("call_time = %s")
                            valores_update.append(info['call_time'])
                            campos_actualizados['call_time'] += 1

                        # call_summary
                        if info['call_summary'] and (not lead['call_summary'] or lead['call_summary'].strip() == ''):
                            campos_update.append("call_summary = %s")
                            valores_update.append(info['call_summary'])
                            campos_actualizados['call_summary'] += 1

                        # call_duration
                        if info['call_duration'] and not lead['call_duration']:
                            campos_update.append("call_duration = %s")
                            valores_update.append(info['call_duration'])
                            campos_actualizados['call_duration'] += 1

                        # Actualizar solo si hay campos que actualizar
                        if campos_update:
                            query = f"""
                                UPDATE leads
                                SET {', '.join(campos_update)}
                                WHERE id = %s
                            """
                            valores_update.append(lead['id'])

                            cursor.execute(query, valores_update)
                            leads_actualizados += 1

                            if leads_actualizados % 100 == 0:
                                print(f"  Procesados {leads_actualizados} leads...")
                else:
                    leads_sin_match += 1

            connection.commit()

            print(f"\nACTUALIZACIÓN COMPLETADA:")
            print(f"  Leads actualizados: {leads_actualizados}")
            print(f"  Teléfonos sin match en leads: {leads_sin_match}")
            print(f"  Campos actualizados:")
            for campo, count in campos_actualizados.items():
                print(f"    {campo}: {count}")

            # Verificar resultado final
            cursor.execute("""
                SELECT
                    COUNT(*) as total_leads,
                    COUNT(CASE WHEN call_id IS NOT NULL AND call_id != '' THEN 1 END) as call_id_completos,
                    COUNT(CASE WHEN call_summary IS NOT NULL AND call_summary != '' THEN 1 END) as call_summary_completos,
                    COUNT(CASE WHEN call_time IS NOT NULL THEN 1 END) as call_time_completos,
                    COUNT(CASE WHEN call_duration IS NOT NULL THEN 1 END) as call_duration_completos
                FROM leads
            """)

            stats_final = cursor.fetchone()
            print(f"\nESTADÍSTICAS FINALES:")
            print(f"  Total leads: {stats_final['total_leads']}")
            print(f"  call_id completados: {stats_final['call_id_completos']} ({stats_final['call_id_completos']/stats_final['total_leads']*100:.1f}%)")
            print(f"  call_summary completados: {stats_final['call_summary_completos']} ({stats_final['call_summary_completos']/stats_final['total_leads']*100:.1f}%)")
            print(f"  call_time completados: {stats_final['call_time_completos']} ({stats_final['call_time_completos']/stats_final['total_leads']*100:.1f}%)")
            print(f"  call_duration completados: {stats_final['call_duration_completos']} ({stats_final['call_duration_completos']/stats_final['total_leads']*100:.1f}%)")

            # Mostrar ejemplos de leads actualizados
            print(f"\nEJEMPLOS DE LEADS ACTUALIZADOS:")
            cursor.execute("""
                SELECT id, nombre, telefono, call_id, call_summary, call_time, call_duration
                FROM leads
                WHERE call_id IS NOT NULL AND call_id != ''
                ORDER BY id
                LIMIT 5
            """)

            for lead in cursor.fetchall():
                summary_preview = lead['call_summary'][:50] + '...' if lead['call_summary'] else 'None'
                print(f"  ID {lead['id']}: {lead['nombre']} | Tel: {lead['telefono']}")
                print(f"    call_id: {lead['call_id']} | time: {lead['call_time']} | duration: {lead['call_duration']}s")
                print(f"    summary: {summary_preview}")

    except Exception as e:
        print(f"Error durante la actualización: {e}")
        import traceback
        traceback.print_exc()
        connection.rollback()
    finally:
        connection.close()

def main():
    print("ACTUALIZADOR DE CAMPOS DE LLAMADA DESDE EXCEL")
    print("=" * 50)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Procesar Excel
    info_llamadas = procesar_excel_llamadas()

    if info_llamadas:
        # Actualizar base de datos
        actualizar_campos_llamada(info_llamadas)
        print("\nProceso completado exitosamente.")
    else:
        print("\nNo se pudo procesar el archivo Excel.")

if __name__ == "__main__":
    main()
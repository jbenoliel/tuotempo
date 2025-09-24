"""
Script para exportar todos los leads de SEGURCAIXA_JULIO con todos los campos
"""

import pymysql
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def exportar_segurcaixa_julio():
    """Exporta todos los leads de SEGURCAIXA_JULIO con información completa"""

    # Conectar a la base de datos
    conn = pymysql.connect(
        host=os.getenv('MYSQLHOST'),
        port=int(os.getenv('MYSQLPORT')),
        user=os.getenv('MYSQLUSER'),
        password=os.getenv('MYSQLPASSWORD'),
        database=os.getenv('MYSQLDATABASE'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        print('EXPORTANDO LEADS DE SEGURCAIXA_JULIO CON TODOS LOS CAMPOS')
        print('=' * 60)

        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            ORDER BY id
        ''')

        leads = cursor.fetchall()
        print(f'Leads encontrados: {len(leads)}')

        if leads:
            # Convertir a DataFrame
            df = pd.DataFrame(leads)

            # Nombre del archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archivo = f'leads_SEGURCAIXA_JULIO_completo_{timestamp}.xlsx'

            # Exportar a Excel con múltiples hojas
            with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
                # Hoja principal con todos los datos
                df.to_excel(writer, sheet_name='Leads_Completos', index=False)

                # Hoja de resumen/estadísticas
                resumen_data = {
                    'Estadistica': [
                        'Total leads',
                        'Fecha exportacion',
                        'Leads abiertos',
                        'Leads cerrados',
                        'Con intentos de llamada',
                        'Promedio intentos',
                        'Maximo intentos',
                        'Con call_id',
                        'Con call_summary',
                        'Con call_time',
                        'Con call_duration',
                        'Con cita agendada',
                        'Con email',
                        'Con telefono'
                    ],
                    'Valor': [
                        len(df),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        len(df[df['lead_status'] == 'open']),
                        len(df[df['lead_status'] == 'closed']),
                        len(df[df['call_attempts_count'] > 0]),
                        round(df['call_attempts_count'].mean(), 2),
                        df['call_attempts_count'].max(),
                        len(df[df['call_id'].notna()]),
                        len(df[df['call_summary'].notna() & (df['call_summary'] != '')]),
                        len(df[df['call_time'].notna()]),
                        len(df[df['call_duration'].notna()]),
                        len(df[df['cita'].notna()]),
                        len(df[df['email'].notna()]),
                        len(df[df['telefono'].notna()])
                    ]
                }

                df_resumen = pd.DataFrame(resumen_data)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

                # Hoja con leads que tienen cita
                df_con_cita = df[df['cita'].notna()]
                if not df_con_cita.empty:
                    df_con_cita.to_excel(writer, sheet_name='Leads_Con_Cita', index=False)
                    print(f'  Leads con cita: {len(df_con_cita)}')

                # Hoja con leads con más llamadas (5 o más)
                df_mas_llamadas = df[df['call_attempts_count'] >= 5].sort_values('call_attempts_count', ascending=False)
                if not df_mas_llamadas.empty:
                    df_mas_llamadas.to_excel(writer, sheet_name='Mas_Llamadas', index=False)
                    print(f'  Leads con 5+ llamadas: {len(df_mas_llamadas)}')

                # Hoja con leads con call_summary
                df_con_summary = df[df['call_summary'].notna() & (df['call_summary'] != '')]
                if not df_con_summary.empty:
                    df_con_summary.to_excel(writer, sheet_name='Con_Summary', index=False)
                    print(f'  Leads con summary: {len(df_con_summary)}')

            print(f'\\nArchivo exportado: {archivo}')
            print(f'Registros: {len(df)}')
            print(f'Columnas: {len(df.columns)}')

            # Estadísticas detalladas
            print(f'\\nEstadisticas detalladas:')
            print(f'  Leads abiertos: {len(df[df["lead_status"] == "open"])}')
            print(f'  Leads cerrados: {len(df[df["lead_status"] == "closed"])}')
            print(f'  Con intentos llamada: {len(df[df["call_attempts_count"] > 0])}')
            print(f'  Promedio intentos: {df["call_attempts_count"].mean():.2f}')
            print(f'  Con call_id: {len(df[df["call_id"].notna()])}')
            print(f'  Con call_summary: {len(df[df["call_summary"].notna() & (df["call_summary"] != "")])}')
            print(f'  Con call_time: {len(df[df["call_time"].notna()])}')
            print(f'  Con cita: {len(df[df["cita"].notna()])}')
            print(f'  Con email: {len(df[df["email"].notna()])}')

            # Mostrar nombres de columnas
            print(f'\\nColumnas incluidas ({len(df.columns)}):')
            for i, col in enumerate(df.columns, 1):
                print(f'  {i:2d}. {col}')

            print(f'\\nUbicacion del archivo:')
            print(f'  C:\\Users\\jbeno\\CascadeProjects\\tuotempo\\{archivo}')

        else:
            print('No se encontraron leads de SEGURCAIXA_JULIO')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    exportar_segurcaixa_julio()
"""
Script para exportar la tabla leads en dos archivos Excel separados,
uno por cada valor del campo origen_archivo.
"""

import os
import pandas as pd
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Crear conexion a la base de datos Railway"""
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

def exportar_leads_por_origen():
    """
    Exporta los leads en archivos Excel separados por origen_archivo
    """

    connection = get_db_connection()
    if not connection:
        return

    try:
        print("EXPORTADOR DE LEADS POR ORIGEN_ARCHIVO")
        print("=" * 45)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Obtener los valores distintos de origen_archivo
        query_origenes = """
        SELECT DISTINCT origen_archivo, COUNT(*) as cantidad
        FROM leads
        WHERE origen_archivo IS NOT NULL
        GROUP BY origen_archivo
        ORDER BY origen_archivo
        """

        df_origenes = pd.read_sql(query_origenes, connection)

        print("Origenes de archivo encontrados:")
        for _, row in df_origenes.iterrows():
            print(f"  '{row['origen_archivo']}': {row['cantidad']} leads")
        print()

        # Query para obtener todos los campos de leads
        query_leads = """
        SELECT *
        FROM leads
        WHERE origen_archivo = %s
        ORDER BY id
        """

        # Exportar cada origen a un archivo Excel separado
        for _, origen_row in df_origenes.iterrows():
            origen = origen_row['origen_archivo']
            cantidad = origen_row['cantidad']

            print(f"Exportando {origen} ({cantidad} leads)...")

            # Obtener leads de este origen
            df_leads = pd.read_sql(query_leads, connection, params=[origen])

            # Limpiar nombre de archivo
            nombre_archivo_limpio = origen.replace(' ', '_').replace('/', '_').replace('\\', '_')
            archivo_excel = f"leads_{nombre_archivo_limpio}.xlsx"

            # Exportar a Excel
            with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
                df_leads.to_excel(writer, sheet_name='Leads', index=False)

                # Crear una hoja de resumen
                resumen_data = {
                    'Estadistica': [
                        'Origen archivo',
                        'Total leads',
                        'Fecha exportacion',
                        'Leads con intentos de llamada',
                        'Promedio intentos por lead',
                        'Leads abiertos',
                        'Leads cerrados',
                        'Leads con cita',
                        'Leads con telefono',
                        'Leads con email'
                    ],
                    'Valor': [
                        origen,
                        len(df_leads),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        len(df_leads[df_leads['call_attempts_count'] > 0]),
                        round(df_leads['call_attempts_count'].mean(), 2) if not df_leads['call_attempts_count'].empty else 0,
                        len(df_leads[df_leads['lead_status'] == 'open']),
                        len(df_leads[df_leads['lead_status'] == 'closed']),
                        len(df_leads[df_leads['cita'].notna()]),
                        len(df_leads[df_leads['telefono'].notna()]),
                        len(df_leads[df_leads['email'].notna()])
                    ]
                }

                df_resumen = pd.DataFrame(resumen_data)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

            print(f"  Archivo generado: {archivo_excel}")
            print(f"  Registros: {len(df_leads)}")
            print(f"  Columnas: {len(df_leads.columns)}")

            # Mostrar algunas estadisticas
            print(f"  Leads abiertos: {len(df_leads[df_leads['lead_status'] == 'open'])}")
            print(f"  Leads cerrados: {len(df_leads[df_leads['lead_status'] == 'closed'])}")
            print(f"  Con intentos de llamada: {len(df_leads[df_leads['call_attempts_count'] > 0])}")
            promedio_intentos = df_leads['call_attempts_count'].mean()
            if pd.isna(promedio_intentos):
                promedio_intentos = 0
            print(f"  Promedio intentos: {promedio_intentos:.2f}")
            print()

        # Crear tambien un archivo combinado con todos los leads
        print("Creando archivo combinado con todos los leads...")

        query_todos = """
        SELECT *
        FROM leads
        ORDER BY origen_archivo, id
        """

        df_todos = pd.read_sql(query_todos, connection)

        archivo_combinado = f"leads_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(archivo_combinado, engine='openpyxl') as writer:
            # Hoja con todos los leads
            df_todos.to_excel(writer, sheet_name='Todos_los_leads', index=False)

            # Hoja separada por origen
            for origen in df_todos['origen_archivo'].unique():
                if pd.notna(origen):
                    df_origen = df_todos[df_todos['origen_archivo'] == origen]
                    nombre_hoja = origen[:30]  # Limite de caracteres para nombre de hoja
                    df_origen.to_excel(writer, sheet_name=nombre_hoja, index=False)

            # Hoja de estadisticas generales
            estadisticas_data = {
                'Origen': [],
                'Total_leads': [],
                'Leads_abiertos': [],
                'Leads_cerrados': [],
                'Con_llamadas': [],
                'Promedio_intentos': [],
                'Con_cita': [],
                'Con_telefono': [],
                'Con_email': []
            }

            for origen in df_todos['origen_archivo'].unique():
                if pd.notna(origen):
                    df_origen = df_todos[df_todos['origen_archivo'] == origen]
                    estadisticas_data['Origen'].append(origen)
                    estadisticas_data['Total_leads'].append(len(df_origen))
                    estadisticas_data['Leads_abiertos'].append(len(df_origen[df_origen['lead_status'] == 'open']))
                    estadisticas_data['Leads_cerrados'].append(len(df_origen[df_origen['lead_status'] == 'closed']))
                    estadisticas_data['Con_llamadas'].append(len(df_origen[df_origen['call_attempts_count'] > 0]))
                    promedio = df_origen['call_attempts_count'].mean()
                    estadisticas_data['Promedio_intentos'].append(round(promedio, 2) if not pd.isna(promedio) else 0)
                    estadisticas_data['Con_cita'].append(len(df_origen[df_origen['cita'].notna()]))
                    estadisticas_data['Con_telefono'].append(len(df_origen[df_origen['telefono'].notna()]))
                    estadisticas_data['Con_email'].append(len(df_origen[df_origen['email'].notna()]))

            df_estadisticas = pd.DataFrame(estadisticas_data)
            df_estadisticas.to_excel(writer, sheet_name='Estadisticas', index=False)

        print(f"Archivo combinado generado: {archivo_combinado}")
        print(f"Total registros: {len(df_todos)}")
        print()

        print("EXPORTACION COMPLETADA")
        print("=" * 25)
        print("Archivos generados:")
        for _, origen_row in df_origenes.iterrows():
            origen = origen_row['origen_archivo']
            nombre_archivo_limpio = origen.replace(' ', '_').replace('/', '_').replace('\\', '_')
            print(f"  leads_{nombre_archivo_limpio}.xlsx")
        print(f"  {archivo_combinado}")

    except Exception as e:
        print(f"Error durante la exportacion: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    exportar_leads_por_origen()
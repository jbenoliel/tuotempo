"""
Script simplificado para exportar la tabla leads por origen_archivo
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

def exportar_leads():
    """Exportar leads por origen_archivo"""

    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            print("EXPORTANDO LEADS POR ORIGEN_ARCHIVO")
            print("=" * 40)

            # Primero verificar los origenes
            cursor.execute("""
                SELECT DISTINCT origen_archivo, COUNT(*) as cantidad
                FROM leads
                WHERE origen_archivo IS NOT NULL
                GROUP BY origen_archivo
                ORDER BY origen_archivo
            """)

            origenes = cursor.fetchall()

            print("Origenes encontrados:")
            for origen in origenes:
                print(f"  {origen['origen_archivo']}: {origen['cantidad']} leads")
            print()

            # Exportar cada origen
            for origen_data in origenes:
                origen = origen_data['origen_archivo']
                print(f"Exportando origen: {origen}...")

                # Obtener todos los leads de este origen
                cursor.execute("""
                    SELECT * FROM leads
                    WHERE origen_archivo = %s
                    ORDER BY id
                """, (origen,))

                leads = cursor.fetchall()

                if leads:
                    # Convertir a DataFrame
                    df = pd.DataFrame(leads)

                    # Nombre de archivo limpio con timestamp
                    nombre_limpio = origen.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    archivo = f"leads_{nombre_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                    # Exportar a Excel
                    df.to_excel(archivo, index=False, engine='openpyxl')

                    print(f"  Archivo creado: {archivo}")
                    print(f"  Registros: {len(df)}")
                    print(f"  Columnas: {len(df.columns)}")

                    # Estadisticas basicas
                    leads_abiertos = len(df[df['lead_status'] == 'open'])
                    leads_cerrados = len(df[df['lead_status'] == 'closed'])
                    con_llamadas = len(df[df['call_attempts_count'] > 0])

                    print(f"  Leads abiertos: {leads_abiertos}")
                    print(f"  Leads cerrados: {leads_cerrados}")
                    print(f"  Con intentos de llamada: {con_llamadas}")
                    print()

            print("EXPORTACION COMPLETADA")

    except Exception as e:
        print(f"Error durante la exportacion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection.close()

if __name__ == "__main__":
    exportar_leads()
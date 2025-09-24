"""
Script para actualizar status_level_1 y status_level_2 desde el archivo Excel de SEGURCAIXA_JULIO
"""

import pandas as pd
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

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

def actualizar_segurcaixa():
    """Actualizar status de SEGURCAIXA_JULIO"""

    archivo_excel = 'leads_SEGURCAIXA_JULIO_completo_20250922_115315.xlsx'

    print("ACTUALIZANDO STATUS DE SEGURCAIXA_JULIO")
    print("=" * 45)
    print(f"Archivo: {archivo_excel}")

    try:
        # Leer Excel
        df = pd.read_excel(archivo_excel, sheet_name='Leads_Completos')
        print(f"Registros leidos: {len(df)}")

        # Verificar columnas
        if 'id' not in df.columns or 'status_level_1' not in df.columns:
            print("ERROR: Faltan columnas necesarias")
            return

        # Conectar a BD
        connection = get_db_connection()
        if not connection:
            return

        with connection.cursor() as cursor:
            cambios_aplicados = 0
            errores = 0

            print("Procesando cambios...")

            for _, row in df.iterrows():
                try:
                    lead_id = int(row['id'])
                    nuevo_status_1 = str(row['status_level_1']) if pd.notna(row['status_level_1']) else None
                    nuevo_status_2 = str(row['status_level_2']) if pd.notna(row['status_level_2']) else None

                    # Obtener datos actuales
                    cursor.execute("""
                        SELECT status_level_1, status_level_2, nombre
                        FROM leads
                        WHERE id = %s AND origen_archivo = 'SEGURCAIXA_JULIO'
                    """, (lead_id,))

                    lead_actual = cursor.fetchone()

                    if lead_actual:
                        actual_1 = str(lead_actual['status_level_1']) if lead_actual['status_level_1'] else None
                        actual_2 = str(lead_actual['status_level_2']) if lead_actual['status_level_2'] else None

                        # Verificar cambios
                        if nuevo_status_1 != actual_1 or nuevo_status_2 != actual_2:
                            # Actualizar
                            cursor.execute("""
                                UPDATE leads
                                SET status_level_1 = %s, status_level_2 = %s, updated_at = %s
                                WHERE id = %s
                            """, (nuevo_status_1, nuevo_status_2, datetime.now(), lead_id))

                            cambios_aplicados += 1

                            if cambios_aplicados <= 5:  # Mostrar primeros 5 cambios
                                print(f"  ID {lead_id} ({lead_actual['nombre']}):")
                                if nuevo_status_1 != actual_1:
                                    print(f"    status_level_1: '{actual_1}' -> '{nuevo_status_1}'")
                                if nuevo_status_2 != actual_2:
                                    print(f"    status_level_2: '{actual_2}' -> '{nuevo_status_2}'")

                            if cambios_aplicados % 50 == 0:
                                print(f"  Procesados {cambios_aplicados} cambios...")

                except Exception as e:
                    errores += 1
                    if errores <= 3:  # Mostrar primeros errores
                        print(f"  Error en fila {row.name}: {e}")

            # Confirmar cambios
            connection.commit()

            print(f"\nRESULTADO:")
            print(f"  Cambios aplicados: {cambios_aplicados}")
            print(f"  Errores: {errores}")

            # Verificar estadísticas finales
            cursor.execute("""
                SELECT
                    status_level_1,
                    COUNT(*) as cantidad
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                GROUP BY status_level_1
                ORDER BY cantidad DESC
                LIMIT 10
            """)

            print(f"\nEstadisticas de status_level_1 actualizadas:")
            for stat in cursor.fetchall():
                print(f"  {stat['status_level_1']}: {stat['cantidad']} leads")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    actualizar_segurcaixa()
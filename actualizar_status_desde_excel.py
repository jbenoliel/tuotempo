"""
Script para actualizar los campos status_level_1 y status_level_2 en la base de datos
basándose en los cambios realizados en los archivos Excel por origen de archivo.
"""

import os
import pandas as pd
import pymysql
from datetime import datetime
from dotenv import load_dotenv

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

def leer_archivos_excel():
    """Leer los archivos Excel y extraer los datos de status_level"""

    archivos_excel = {
        'SEGURCAIXA_JULIO': None,
        'Septiembre': None
    }

    # Buscar los archivos más recientes de cada origen
    archivos_encontrados = []

    # Buscar archivos SEGURCAIXA_JULIO
    import glob
    segurcaixa_files = glob.glob('leads_SEGURCAIXA_JULIO_*20250922*.xlsx')
    if segurcaixa_files:
        # Tomar el más reciente
        segurcaixa_files.sort()
        archivos_excel['SEGURCAIXA_JULIO'] = segurcaixa_files[-1]
        archivos_encontrados.append(segurcaixa_files[-1])

    # Buscar archivos Septiembre
    septiembre_files = glob.glob('leads_Septiembre_*20250922*.xlsx')
    if septiembre_files:
        # Tomar el más reciente
        septiembre_files.sort()
        archivos_excel['Septiembre'] = septiembre_files[-1]
        archivos_encontrados.append(septiembre_files[-1])

    print("LEYENDO ARCHIVOS EXCEL CON CAMBIOS")
    print("=" * 40)
    print(f"Archivos encontrados: {len(archivos_encontrados)}")

    datos_excel = {}

    for origen, archivo in archivos_excel.items():
        if archivo:
            print(f"\nProcesando {origen}: {archivo}")

            try:
                # Leer Excel - intentar diferentes métodos
                try:
                    df = pd.read_excel(archivo, engine='openpyxl')
                except:
                    try:
                        df = pd.read_excel(archivo, engine='xlrd')
                    except:
                        df = pd.read_excel(archivo)

                print(f"  Registros leidos: {len(df)}")

                # Verificar que tiene las columnas necesarias
                if 'id' not in df.columns or 'status_level_1' not in df.columns or 'status_level_2' not in df.columns:
                    print(f"  ERROR: El archivo {archivo} no tiene las columnas necesarias")
                    continue

                # Extraer solo los campos necesarios
                df_status = df[['id', 'status_level_1', 'status_level_2']].copy()

                # Limpiar valores NaN
                df_status['status_level_1'] = df_status['status_level_1'].fillna('')
                df_status['status_level_2'] = df_status['status_level_2'].fillna('')

                datos_excel[origen] = df_status
                print(f"  Datos extraídos: {len(df_status)} registros")

                # Mostrar algunos ejemplos
                print(f"  Ejemplos de status_level_1:")
                status_counts = df_status['status_level_1'].value_counts().head(5)
                for status, count in status_counts.items():
                    if status.strip():  # Solo mostrar valores no vacíos
                        print(f"    {status}: {count} leads")

            except Exception as e:
                print(f"  ERROR leyendo {archivo}: {e}")
                continue
        else:
            print(f"\nNo se encontró archivo para {origen}")

    return datos_excel

def comparar_con_bd(datos_excel):
    """Comparar datos del Excel con los actuales de la base de datos"""

    connection = get_db_connection()
    if not connection:
        return None

    cambios_detectados = {}

    try:
        with connection.cursor() as cursor:
            print("\n" + "=" * 50)
            print("COMPARANDO CON BASE DE DATOS ACTUAL")
            print("=" * 50)

            for origen, df_excel in datos_excel.items():
                print(f"\nProcesando origen: {origen}")

                cambios_origen = []

                for _, row in df_excel.iterrows():
                    lead_id = row['id']
                    nuevo_status_1 = str(row['status_level_1']).strip()
                    nuevo_status_2 = str(row['status_level_2']).strip()

                    # Obtener datos actuales de la BD
                    cursor.execute("""
                        SELECT status_level_1, status_level_2, nombre, apellidos
                        FROM leads
                        WHERE id = %s
                    """, (lead_id,))

                    lead_actual = cursor.fetchone()

                    if lead_actual:
                        actual_status_1 = str(lead_actual['status_level_1'] or '').strip()
                        actual_status_2 = str(lead_actual['status_level_2'] or '').strip()

                        # Verificar si hay cambios
                        cambio_status_1 = nuevo_status_1 != actual_status_1
                        cambio_status_2 = nuevo_status_2 != actual_status_2

                        if cambio_status_1 or cambio_status_2:
                            cambios_origen.append({
                                'id': lead_id,
                                'nombre': lead_actual['nombre'],
                                'apellidos': lead_actual['apellidos'],
                                'actual_status_1': actual_status_1,
                                'nuevo_status_1': nuevo_status_1,
                                'actual_status_2': actual_status_2,
                                'nuevo_status_2': nuevo_status_2,
                                'cambio_status_1': cambio_status_1,
                                'cambio_status_2': cambio_status_2
                            })

                cambios_detectados[origen] = cambios_origen
                print(f"  Cambios detectados: {len(cambios_origen)}")

                # Mostrar algunos ejemplos
                if cambios_origen:
                    print(f"  Ejemplos de cambios:")
                    for cambio in cambios_origen[:3]:
                        print(f"    ID {cambio['id']} ({cambio['nombre']} {cambio['apellidos']}):")
                        if cambio['cambio_status_1']:
                            print(f"      status_level_1: '{cambio['actual_status_1']}' -> '{cambio['nuevo_status_1']}'")
                        if cambio['cambio_status_2']:
                            print(f"      status_level_2: '{cambio['actual_status_2']}' -> '{cambio['nuevo_status_2']}'")

    except Exception as e:
        print(f"Error comparando con BD: {e}")
        return None
    finally:
        connection.close()

    return cambios_detectados

def aplicar_cambios(cambios_detectados):
    """Aplicar los cambios a la base de datos"""

    if not cambios_detectados:
        print("No hay cambios para aplicar")
        return

    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            print("\n" + "=" * 50)
            print("APLICANDO CAMBIOS A LA BASE DE DATOS")
            print("=" * 50)

            total_cambios = 0

            for origen, cambios in cambios_detectados.items():
                if not cambios:
                    continue

                print(f"\nActualizando {origen}: {len(cambios)} cambios")

                for cambio in cambios:
                    # Construir la query de actualización
                    campos_update = []
                    valores_update = []

                    if cambio['cambio_status_1']:
                        campos_update.append("status_level_1 = %s")
                        valores_update.append(cambio['nuevo_status_1'] if cambio['nuevo_status_1'] else None)

                    if cambio['cambio_status_2']:
                        campos_update.append("status_level_2 = %s")
                        valores_update.append(cambio['nuevo_status_2'] if cambio['nuevo_status_2'] else None)

                    if campos_update:
                        # Agregar timestamp de actualización
                        campos_update.append("updated_at = %s")
                        valores_update.append(datetime.now())

                        query = f"""
                            UPDATE leads
                            SET {', '.join(campos_update)}
                            WHERE id = %s
                        """
                        valores_update.append(cambio['id'])

                        cursor.execute(query, valores_update)
                        total_cambios += 1

                        if total_cambios % 50 == 0:
                            print(f"  Aplicados {total_cambios} cambios...")

            # Confirmar cambios
            connection.commit()

            print(f"\nCambios aplicados exitosamente: {total_cambios}")

            # Verificar algunos resultados
            print(f"\nVerificando resultados...")
            for origen, cambios in cambios_detectados.items():
                if cambios:
                    # Verificar el primer cambio
                    primer_cambio = cambios[0]
                    cursor.execute("""
                        SELECT status_level_1, status_level_2, updated_at
                        FROM leads
                        WHERE id = %s
                    """, (primer_cambio['id'],))

                    resultado = cursor.fetchone()
                    if resultado:
                        print(f"  {origen} - ID {primer_cambio['id']}: status_level_1='{resultado['status_level_1']}', status_level_2='{resultado['status_level_2']}'")

    except Exception as e:
        print(f"Error aplicando cambios: {e}")
        connection.rollback()
        import traceback
        traceback.print_exc()
    finally:
        connection.close()

def main():
    print("ACTUALIZADOR DE STATUS_LEVEL DESDE EXCEL")
    print("=" * 50)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Leer archivos Excel
    datos_excel = leer_archivos_excel()

    if not datos_excel:
        print("No se pudieron leer los archivos Excel")
        return

    # Comparar con BD actual
    cambios_detectados = comparar_con_bd(datos_excel)

    if not cambios_detectados:
        print("No se pudieron detectar cambios")
        return

    # Mostrar resumen de cambios
    total_cambios = sum(len(cambios) for cambios in cambios_detectados.values())
    print(f"\nRESUMEN DE CAMBIOS DETECTADOS:")
    print(f"Total cambios a aplicar: {total_cambios}")

    if total_cambios > 0:
        print("\n¿Desea aplicar estos cambios? Los cambios se aplicarán automáticamente...")
        # Aplicar cambios
        aplicar_cambios(cambios_detectados)
    else:
        print("No hay cambios que aplicar")

if __name__ == "__main__":
    main()
"""
Script para actualizar call_attempts_count usando el Excel con todas las llamadas de la campana.
El archivo contiene el telefono en el campo 'To' con prefijo de pais (34).
"""

import os
import sys
import pandas as pd
import pymysql
from datetime import datetime
from dotenv import load_dotenv
from collections import Counter
import re

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

def limpiar_telefono(telefono):
    """
    Limpia el numero de telefono removiendo el codigo de pais y caracteres no numericos
    """
    if pd.isna(telefono):
        return None

    # Convertir a string
    telefono_str = str(telefono)

    # Remover todos los caracteres no numericos
    telefono_limpio = re.sub(r'[^0-9]', '', telefono_str)

    # Remover codigo de pais 34 si esta presente
    if telefono_limpio.startswith('34') and len(telefono_limpio) > 9:
        telefono_limpio = telefono_limpio[2:]

    # Validar que tenga 9 digitos
    if len(telefono_limpio) == 9:
        return telefono_limpio

    return None

def leer_excel_llamadas():
    """
    Lee el archivo Excel con todas las llamadas y cuenta las llamadas por telefono
    """
    excel_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\Total llamadas.xlsx"

    print(f"Leyendo archivo Excel: {excel_path}")

    try:
        # Leer el Excel
        df = pd.read_excel(excel_path)

        print(f"Archivo leido exitosamente. Registros: {len(df)}")
        print(f"Columnas disponibles: {list(df.columns)}")

        # Verificar si existe la columna 'To'
        if 'To' not in df.columns:
            print("ERROR: No se encontro la columna 'To' en el archivo Excel")
            print("Columnas disponibles:", list(df.columns))
            return None

        # Limpiar los telefonos y contar llamadas
        print("\nProcesando telefonos...")
        telefonos_limpios = df['To'].apply(limpiar_telefono)
        telefonos_validos = telefonos_limpios.dropna()

        print(f"Telefonos procesados: {len(df)}")
        print(f"Telefonos validos: {len(telefonos_validos)}")
        print(f"Telefonos invalidos o faltantes: {len(df) - len(telefonos_validos)}")

        # Contar llamadas por telefono
        contador_llamadas = Counter(telefonos_validos)

        print(f"Telefonos unicos con llamadas: {len(contador_llamadas)}")

        # Mostrar algunos ejemplos
        print("\nEjemplos de llamadas por telefono:")
        for telefono, count in list(contador_llamadas.most_common(10)):
            print(f"  {telefono}: {count} llamadas")

        # Estadisticas
        total_llamadas = sum(contador_llamadas.values())
        promedio_llamadas = total_llamadas / len(contador_llamadas)
        max_llamadas = max(contador_llamadas.values())

        print(f"\nEstadisticas:")
        print(f"  Total llamadas: {total_llamadas}")
        print(f"  Promedio llamadas por telefono: {promedio_llamadas:.2f}")
        print(f"  Maximo llamadas a un telefono: {max_llamadas}")

        return contador_llamadas

    except Exception as e:
        print(f"Error leyendo el archivo Excel: {e}")
        return None

def actualizar_call_attempts_count(contador_llamadas):
    """
    Actualiza la tabla leads con el numero real de llamadas desde el Excel
    """
    if not contador_llamadas:
        print("No hay datos de llamadas para procesar")
        return

    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            print("\n=== ACTUALIZANDO CALL_ATTEMPTS_COUNT DESDE EXCEL ===")

            # Primero resetear todos los contadores a 0
            print("Reseteando todos los contadores a 0...")
            cursor.execute("UPDATE leads SET call_attempts_count = 0")

            # Actualizar contadores basandose en el Excel
            leads_actualizados = 0
            leads_no_encontrados = 0

            print("Actualizando contadores basandose en Excel...")

            for telefono, num_llamadas in contador_llamadas.items():
                # Buscar leads que coincidan con este telefono
                cursor.execute("""
                    SELECT id, nombre, telefono
                    FROM leads
                    WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s
                """, (telefono,))

                leads_coincidentes = cursor.fetchall()

                if leads_coincidentes:
                    # Actualizar todos los leads con este telefono
                    for lead in leads_coincidentes:
                        cursor.execute("""
                            UPDATE leads
                            SET call_attempts_count = %s
                            WHERE id = %s
                        """, (num_llamadas, lead['id']))

                        leads_actualizados += 1

                        if leads_actualizados % 100 == 0:
                            print(f"  Procesados {leads_actualizados} leads...")
                else:
                    leads_no_encontrados += 1

            connection.commit()

            print(f"\nActualizacion completada:")
            print(f"  Leads actualizados: {leads_actualizados}")
            print(f"  Telefonos del Excel sin match en leads: {leads_no_encontrados}")

            # Verificar resultados
            cursor.execute("""
                SELECT
                    COUNT(*) as total_leads,
                    COUNT(CASE WHEN call_attempts_count > 0 THEN 1 END) as leads_con_llamadas,
                    AVG(call_attempts_count) as promedio_intentos,
                    MAX(call_attempts_count) as maximo_intentos,
                    SUM(call_attempts_count) as total_intentos
                FROM leads
            """)

            stats = cursor.fetchone()
            print(f"\nEstadisticas finales en la base de datos:")
            print(f"  Total leads: {stats['total_leads']}")
            print(f"  Leads con llamadas: {stats['leads_con_llamadas']}")
            print(f"  Promedio intentos por lead: {stats['promedio_intentos']:.2f}")
            print(f"  Maximo intentos: {stats['maximo_intentos']}")
            print(f"  Total intentos registrados: {stats['total_intentos']}")

            # Mostrar algunos ejemplos
            cursor.execute("""
                SELECT id, nombre, telefono, call_attempts_count
                FROM leads
                WHERE call_attempts_count > 0
                ORDER BY call_attempts_count DESC
                LIMIT 10
            """)

            ejemplos = cursor.fetchall()
            print(f"\nEjemplos de leads con mas llamadas:")
            for ejemplo in ejemplos:
                print(f"  ID {ejemplo['id']} - {ejemplo['nombre']} ({ejemplo['telefono']}): {ejemplo['call_attempts_count']} llamadas")

    except Exception as e:
        print(f"Error durante la actualizacion: {e}")
        connection.rollback()
    finally:
        connection.close()

def main():
    print("ACTUALIZADOR DE CALL_ATTEMPTS_COUNT DESDE EXCEL")
    print("=" * 50)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Leer Excel y contar llamadas
    contador_llamadas = leer_excel_llamadas()

    if contador_llamadas:
        # Actualizar base de datos
        actualizar_call_attempts_count(contador_llamadas)
        print("\nProceso completado exitosamente.")
    else:
        print("\nNo se pudo procesar el archivo Excel.")

if __name__ == "__main__":
    main()
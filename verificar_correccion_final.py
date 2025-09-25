#!/usr/bin/env python3
"""
Verificar que la correccion final funciona
"""

import pymysql
from dotenv import load_dotenv

load_dotenv()

def verificar_correccion():
    """Verificar el calculo corregido de utiles positivos"""

    print("=== VERIFICACION CORRECCION FINAL ===")

    try:
        config = {
            'host': 'ballast.proxy.rlwy.net',
            'port': 11616,
            'user': 'root',
            'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
            'database': 'railway',
            'charset': 'utf8mb4',
            'autocommit': True
        }

        connection = pymysql.connect(**config)
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        archivo_septiembre = "Septiembre"

        print(f"Analizando archivo: {archivo_septiembre}")

        # 1. Conteos individuales
        print(f"\n1. CONTEOS INDIVIDUALES:")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
        """, (archivo_septiembre,))
        citas_agendadas = cursor.fetchone()['count']
        print(f"   Citas Agendadas: {citas_agendadas}")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Manual'
        """, (archivo_septiembre,))
        citas_manuales = cursor.fetchone()['count']
        print(f"   Citas Manuales: {citas_manuales}")

        # 2. Calculo nuevo (simulando la consulta corregida)
        print(f"\n2. CALCULO CORREGIDO:")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (
                TRIM(status_level_1) = 'Cita Agendada'
                OR TRIM(status_level_1) = 'Cita Manual'
            )
        """, (archivo_septiembre,))
        utiles_positivos_corregido = cursor.fetchone()['count']
        print(f"   Utiles Positivos (corregido): {utiles_positivos_corregido}")

        # 3. Simulacion exacta de la consulta del dashboard corregida
        print(f"\n3. SIMULACION DASHBOARD CORREGIDO:")
        cursor.execute("""
            SELECT
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Sin Pack' THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Con Pack' THEN 1 ELSE 0 END), 0) AS cita_con_pack,
                IFNULL(SUM(CASE WHEN (TRIM(status_level_1) = 'Cita Agendada' OR TRIM(status_level_1) = 'Cita Manual') THEN 1 ELSE 0 END), 0) AS utiles_positivos
            FROM leads
            WHERE origen_archivo = %s
        """, (archivo_septiembre,))

        dashboard_data = cursor.fetchone()
        print(f"   Citas sin pack: {dashboard_data['cita_sin_pack']}")
        print(f"   Citas con pack: {dashboard_data['cita_con_pack']}")
        print(f"   UTILES POSITIVOS (dashboard): {dashboard_data['utiles_positivos']}")

        # 4. Verificacion matematica
        print(f"\n4. VERIFICACION:")
        total_esperado = citas_agendadas + citas_manuales
        print(f"   Esperado: {citas_agendadas} + {citas_manuales} = {total_esperado}")
        print(f"   Obtenido: {utiles_positivos_corregido}")
        print(f"   Dashboard: {dashboard_data['utiles_positivos']}")

        if dashboard_data['utiles_positivos'] == total_esperado:
            print(f"   ✓ CORRECTO: El dashboard mostrara {dashboard_data['utiles_positivos']} utiles positivos")
        else:
            print(f"   ✗ ERROR: Hay una discrepancia")

        # 5. Ejemplos de los registros incluidos
        print(f"\n5. EJEMPLOS DE REGISTROS INCLUIDOS:")

        print("   CITAS AGENDADAS:")
        cursor.execute("""
            SELECT nombre, apellidos, status_level_1, status_level_2
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
            LIMIT 3
        """, (archivo_septiembre,))

        for registro in cursor.fetchall():
            print(f"     {registro['nombre']} {registro['apellidos']} - {registro['status_level_1']} / {registro['status_level_2']}")

        print("   CITAS MANUALES:")
        cursor.execute("""
            SELECT nombre, apellidos, status_level_1, status_level_2
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Manual'
            LIMIT 3
        """, (archivo_septiembre,))

        for registro in cursor.fetchall():
            print(f"     {registro['nombre']} {registro['apellidos']} - {registro['status_level_1']} / {registro['status_level_2']}")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_correccion()
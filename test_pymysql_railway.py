#!/usr/bin/env python3
"""
Test usando PyMySQL en lugar de mysql-connector-python
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def test_railway_pymysql():
    """Test connection using PyMySQL"""

    print("=== TEST RAILWAY CON PYMYSQL ===")

    try:
        # Configuracion Railway
        config = {
            'host': 'ballast.proxy.rlwy.net',
            'port': 11616,
            'user': 'root',
            'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
            'database': 'railway',
            'charset': 'utf8mb4',
            'autocommit': True
        }

        print("1. Intentando conectar con PyMySQL...")
        connection = pymysql.connect(**config)
        print("   EXITO: Conexion establecida con PyMySQL")

        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Test basico
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        result = cursor.fetchone()
        print(f"   Total leads: {result['total']}")

        # Archivos disponibles
        cursor.execute("SELECT nombre_archivo, total_registros FROM archivos_origen WHERE activo = 1 ORDER BY nombre_archivo")
        archivos = cursor.fetchall()
        print(f"   Archivos disponibles: {len(archivos)}")

        archivo_septiembre = None
        for archivo in archivos:
            print(f"      - {archivo['nombre_archivo']}: {archivo['total_registros']} registros")
            nombre_lower = archivo['nombre_archivo'].lower()
            if any(x in nombre_lower for x in ['septiembre', 'sep', '09-', '09_']):
                archivo_septiembre = archivo['nombre_archivo']
                print(f"        --> ARCHIVO SEPTIEMBRE: {archivo_septiembre}")

        if not archivo_septiembre and archivos:
            archivo_septiembre = archivos[0]['nombre_archivo']
            print(f"   Usando primer archivo como ejemplo: {archivo_septiembre}")

        if archivo_septiembre:
            print(f"\n2. Analizando {archivo_septiembre}:")

            # Total registros del archivo
            cursor.execute("SELECT COUNT(*) as total FROM leads WHERE origen_archivo = %s", (archivo_septiembre,))
            total = cursor.fetchone()['total']
            print(f"   Total registros en archivo: {total}")

            # Citas agendadas
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE origen_archivo = %s
                AND TRIM(status_level_1) = 'Cita Agendada'
            """, (archivo_septiembre,))
            citas_agendadas = cursor.fetchone()['count']
            print(f"   Citas agendadas: {citas_agendadas}")

            # Citas manuales
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE origen_archivo = %s
                AND cita IS NOT NULL
                AND cita != ''
            """, (archivo_septiembre,))
            citas_manuales = cursor.fetchone()['count']
            print(f"   Citas manuales: {citas_manuales}")

            # Utiles positivos (nueva formula)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE origen_archivo = %s
                AND (TRIM(status_level_1) = 'Cita Agendada' OR (cita IS NOT NULL AND cita != ''))
            """, (archivo_septiembre,))
            utiles_positivos = cursor.fetchone()['count']
            print(f"   UTILES POSITIVOS (nueva formula): {utiles_positivos}")

            # Simulacion dashboard exacta
            cursor.execute("""
                SELECT
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Sin Pack' THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Con Pack' THEN 1 ELSE 0 END), 0) AS cita_con_pack,
                    IFNULL(SUM(CASE WHEN (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL) THEN 1 ELSE 0 END), 0) AS utiles_positivos
                FROM leads
                WHERE origen_archivo = %s
            """, (archivo_septiembre,))
            dashboard_result = cursor.fetchone()

            print(f"\n3. SIMULACION DASHBOARD:")
            print(f"   Citas sin pack: {dashboard_result['cita_sin_pack']}")
            print(f"   Citas con pack: {dashboard_result['cita_con_pack']}")
            print(f"   UTILES POSITIVOS: {dashboard_result['utiles_positivos']}")

            if dashboard_result['utiles_positivos'] == 4:
                print(f"\n4. DIAGNOSTICO PROBLEMA:")
                print("   El dashboard seguiria mostrando 4 utiles positivos")
                print("   Esto significa que realmente solo hay:")
                print(f"   - {citas_agendadas} citas agendadas")
                print(f"   - {citas_manuales} citas manuales adicionales")
                print(f"   - Total: {utiles_positivos} utiles positivos")

                # Verificar que tipo de citas manuales hay
                cursor.execute("""
                    SELECT cita, COUNT(*) as count
                    FROM leads
                    WHERE origen_archivo = %s
                    AND cita IS NOT NULL
                    AND cita != ''
                    GROUP BY cita
                    LIMIT 10
                """, (archivo_septiembre,))
                ejemplos_citas = cursor.fetchall()

                print(f"\n   Ejemplos de citas manuales:")
                for ejemplo in ejemplos_citas:
                    print(f"      '{ejemplo['cita']}': {ejemplo['count']} veces")

            else:
                print(f"\n4. SOLUCION CONFIRMADA:")
                print(f"   El dashboard ahora mostraria {dashboard_result['utiles_positivos']} utiles positivos")
                print(f"   El cambio en el codigo funciono correctamente")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_railway_pymysql()
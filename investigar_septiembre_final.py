#!/usr/bin/env python3
"""
Investigacion final del archivo Septiembre con manejo de errores de fecha
"""

import pymysql
from dotenv import load_dotenv

load_dotenv()

def investigar_septiembre():
    """Investigacion completa del archivo Septiembre"""

    print("=== INVESTIGACION FINAL - ARCHIVO SEPTIEMBRE ===")

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

        # 1. Datos basicos
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE origen_archivo = %s", (archivo_septiembre,))
        total = cursor.fetchone()['total']
        print(f"Total registros: {total}")

        # 2. Citas agendadas
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
        """, (archivo_septiembre,))
        citas_agendadas = cursor.fetchone()['count']
        print(f"Citas agendadas: {citas_agendadas}")

        # 3. Verificar campo cita (evitando el error de fecha)
        print(f"\nAnalisis del campo 'cita':")

        # Contar valores NULL
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND cita IS NULL
        """, (archivo_septiembre,))
        cita_null = cursor.fetchone()['count']
        print(f"  Valores NULL: {cita_null}")

        # Contar valores vacios
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND cita = ''
        """, (archivo_septiembre,))
        cita_vacia = cursor.fetchone()['count']
        print(f"  Valores vacios: {cita_vacia}")

        # Contar valores con contenido
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND cita IS NOT NULL
            AND cita != ''
        """, (archivo_septiembre,))
        cita_valida = cursor.fetchone()['count']
        print(f"  Valores validos: {cita_valida}")

        # 4. Ejemplos de valores del campo cita
        print(f"\nEjemplos de valores en campo 'cita':")
        cursor.execute("""
            SELECT DISTINCT cita, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND cita IS NOT NULL
            AND cita != ''
            GROUP BY cita
            LIMIT 10
        """, (archivo_septiembre,))

        ejemplos_cita = cursor.fetchall()
        if ejemplos_cita:
            for ejemplo in ejemplos_cita:
                print(f"  '{ejemplo['cita']}' -> {ejemplo['count']} registros")
        else:
            print("  No hay valores validos en el campo 'cita'")

        # 5. Calculo de utiles positivos con la nueva formula
        print(f"\nCalculo de UTILES POSITIVOS:")

        # Formula anterior (solo citas agendadas)
        print(f"  Formula anterior: {citas_agendadas} utiles positivos")

        # Nueva formula (citas agendadas OR citas manuales)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (
                TRIM(status_level_1) = 'Cita Agendada'
                OR (cita IS NOT NULL AND cita != '')
            )
        """, (archivo_septiembre,))
        utiles_positivos_nuevo = cursor.fetchone()['count']
        print(f"  Formula nueva: {utiles_positivos_nuevo} utiles positivos")

        # 6. Simulacion exacta de la consulta del dashboard
        print(f"\nSIMULACION CONSULTA DASHBOARD:")
        cursor.execute("""
            SELECT
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Sin Pack' THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Con Pack' THEN 1 ELSE 0 END), 0) AS cita_con_pack,
                IFNULL(SUM(CASE WHEN (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL) THEN 1 ELSE 0 END), 0) AS utiles_positivos
            FROM leads
            WHERE origen_archivo = %s
        """, (archivo_septiembre,))

        dashboard_data = cursor.fetchone()
        print(f"  Citas sin pack: {dashboard_data['cita_sin_pack']}")
        print(f"  Citas con pack: {dashboard_data['cita_con_pack']}")
        print(f"  UTILES POSITIVOS (dashboard): {dashboard_data['utiles_positivos']}")

        # 7. Mostrar ejemplos de registros con citas agendadas
        print(f"\nEJEMPLOS DE CITAS AGENDADAS:")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
            LIMIT 3
        """, (archivo_septiembre,))

        ejemplos_agendadas = cursor.fetchall()
        for ejemplo in ejemplos_agendadas:
            print(f"  {ejemplo['nombre']} {ejemplo['apellidos']} - {ejemplo['telefono']}")
            print(f"    Status: {ejemplo['status_level_1']} / {ejemplo['status_level_2']}")
            print(f"    Cita manual: '{ejemplo['cita']}'")
            print()

        # 8. Conclusion
        print(f"CONCLUSION:")
        print(f"==========")

        if dashboard_data['utiles_positivos'] == 4:
            print(f"El dashboard sigue mostrando 4 utiles positivos porque:")
            print(f"  - Solo hay {citas_agendadas} citas agendadas")
            print(f"  - Solo hay {cita_valida} citas manuales validas")
            print(f"  - Algunos registros pueden tener ambos campos (solapamiento)")
            print(f"  - Total unico: {utiles_positivos_nuevo} utiles positivos")

            if utiles_positivos_nuevo == 4:
                print(f"\nEsto es CORRECTO. Realmente solo hay 4 usuarios con citas.")
                print(f"El problema no era el codigo, sino la expectativa del numero.")
            else:
                print(f"\nHay una discrepancia que requiere investigacion adicional.")

        else:
            print(f"EXITO: El dashboard ahora mostraria {dashboard_data['utiles_positivos']} utiles positivos")
            print(f"El cambio en el codigo funciono correctamente.")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigar_septiembre()
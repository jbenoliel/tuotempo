#!/usr/bin/env python3
"""
Investigar el status correcto para citas manuales
"""

import pymysql
from dotenv import load_dotenv

load_dotenv()

def buscar_citas_manuales():
    """Buscar todos los valores de status_level_1 para identificar citas manuales"""

    print("=== BUSCANDO STATUS DE CITAS MANUALES ===")

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

        # 1. Todos los valores únicos de status_level_1
        print(f"\n1. TODOS LOS STATUS_LEVEL_1 EN SEPTIEMBRE:")
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND status_level_1 IS NOT NULL
            AND status_level_1 != ''
            GROUP BY status_level_1
            ORDER BY count DESC
        """, (archivo_septiembre,))

        status_list = cursor.fetchall()
        for status in status_list:
            print(f"   '{status['status_level_1']}': {status['count']} registros")

        # 2. Buscar específicamente por "cita" en el nombre
        print(f"\n2. STATUS QUE CONTIENEN 'CITA':")
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND status_level_1 IS NOT NULL
            AND LOWER(status_level_1) LIKE '%cita%'
            GROUP BY status_level_1
            ORDER BY count DESC
        """, (archivo_septiembre,))

        cita_status = cursor.fetchall()
        if cita_status:
            for status in cita_status:
                print(f"   '{status['status_level_1']}': {status['count']} registros")
        else:
            print("   No se encontraron status que contengan 'cita'")

        # 3. Buscar por "manual" en el nombre
        print(f"\n3. STATUS QUE CONTIENEN 'MANUAL':")
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND status_level_1 IS NOT NULL
            AND LOWER(status_level_1) LIKE '%manual%'
            GROUP BY status_level_1
            ORDER BY count DESC
        """, (archivo_septiembre,))

        manual_status = cursor.fetchall()
        if manual_status:
            for status in manual_status:
                print(f"   '{status['status_level_1']}': {status['count']} registros")
        else:
            print("   No se encontraron status que contengan 'manual'")

        # 4. Buscar registros con exactamente 21 de count (pista del usuario)
        print(f"\n4. STATUS CON EXACTAMENTE 21 REGISTROS:")
        status_21 = [s for s in status_list if s['count'] == 21]
        if status_21:
            for status in status_21:
                print(f"   *** '{status['status_level_1']}': {status['count']} registros ***")

                # Mostrar ejemplos de estos registros
                cursor.execute("""
                    SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
                    FROM leads
                    WHERE origen_archivo = %s
                    AND status_level_1 = %s
                    LIMIT 3
                """, (archivo_septiembre, status['status_level_1']))

                ejemplos = cursor.fetchall()
                for ejemplo in ejemplos:
                    print(f"       {ejemplo['nombre']} {ejemplo['apellidos']} - {ejemplo['telefono']}")
                    print(f"       Status: {ejemplo['status_level_1']} / {ejemplo['status_level_2']}")
                    print(f"       Cita: '{ejemplo['cita']}'")
                    print()
        else:
            print("   No se encontraron status con exactamente 21 registros")

        # 5. Verificar si hay otros status relacionados con citas
        print(f"\n5. OTROS STATUS POSIBLES (top 10):")
        for status in status_list[:10]:
            if status['status_level_1'] not in ['Cita Agendada', 'No Interesado', 'Volver a llamar']:
                print(f"   '{status['status_level_1']}': {status['count']} registros")

        # 6. Calcular utiles positivos incluyendo el status de 21 registros
        if status_21:
            status_cita_manual = status_21[0]['status_level_1']
            print(f"\n6. CALCULANDO UTILES POSITIVOS INCLUYENDO '{status_cita_manual}':")

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE origen_archivo = %s
                AND (
                    TRIM(status_level_1) = 'Cita Agendada'
                    OR TRIM(status_level_1) = %s
                )
            """, (archivo_septiembre, status_cita_manual))

            utiles_corregidos = cursor.fetchone()['count']
            print(f"   Utiles positivos corregidos: {utiles_corregidos}")
            print(f"   Formula: 'Cita Agendada' OR '{status_cita_manual}'")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    buscar_citas_manuales()
#!/usr/bin/env python3
"""
Busca de donde salen los 28 utiles positivos que menciona el usuario
"""

import pymysql
from datetime import datetime

# Configuracion de Railway
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    return pymysql.connect(**RAILWAY_CONFIG)

def buscar_utiles():
    """Busca todos los posibles 'utiles' o estados que puedan sumar 28"""

    print("=== BUSQUEDA COMPLETA DE LOS 28 UTILES ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        origen_archivo = 'SEGURCAIXA_JULIO'

        # 1. Ver TODOS los status_level_1 existentes
        print("1. TODOS LOS STATUS_LEVEL_1 EXISTENTES:")
        print("=" * 60)

        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            GROUP BY status_level_1
            ORDER BY count DESC
        """, [origen_archivo])

        all_status = cursor.fetchall()
        total_leads = 0

        for status, count in all_status:
            status_str = status if status else 'NULL'
            print(f"   {status_str}: {count}")
            total_leads += count

        print(f"   TOTAL: {total_leads}")
        print()

        # 2. Buscar cualquier cosa que pueda ser interpretada como "util"
        print("2. BUSQUEDA AMPLIA DE 'UTIL' (cualquier variacion):")
        print("=" * 60)

        # Buscar diferentes patrones
        patrones = [
            'util', 'Util', 'UTIL',
            'positiv', 'Positiv', 'POSITIV',
            'interes', 'Interes', 'INTERES',
            'Si', 'si', 'SI',
            'Yes', 'yes', 'YES'
        ]

        encontrados = []

        for patron in patrones:
            cursor.execute(f"""
                SELECT status_level_1, COUNT(*) as count
                FROM leads
                WHERE origen_archivo = %s
                AND status_level_1 LIKE %s
                GROUP BY status_level_1
            """, [origen_archivo, f'%{patron}%'])

            results = cursor.fetchall()
            for status, count in results:
                encontrados.append((status, count))

        if encontrados:
            print("   Estados que contienen palabras clave:")
            unique_encontrados = {}
            for status, count in encontrados:
                if status not in unique_encontrados:
                    unique_encontrados[status] = count

            total_encontrados = 0
            for status, count in unique_encontrados.items():
                print(f"     '{status}': {count}")
                total_encontrados += count

            print(f"   TOTAL ENCONTRADOS: {total_encontrados}")
        else:
            print("   No se encontraron estados con esas palabras clave")

        print()

        # 3. Verificar status_level_2 tambien
        print("3. VERIFICACION EN STATUS_LEVEL_2:")
        print("=" * 60)

        cursor.execute("""
            SELECT status_level_2, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND status_level_2 IS NOT NULL
            GROUP BY status_level_2
            ORDER BY count DESC
        """, [origen_archivo])

        status2_all = cursor.fetchall()

        print("   Todos los status_level_2:")
        for status2, count in status2_all:
            print(f"     '{status2}': {count}")

        print()

        # 4. Buscar patrones en status_level_2
        encontrados_level2 = []

        for patron in patrones:
            cursor.execute(f"""
                SELECT status_level_1, status_level_2, COUNT(*) as count
                FROM leads
                WHERE origen_archivo = %s
                AND status_level_2 LIKE %s
                GROUP BY status_level_1, status_level_2
            """, [origen_archivo, f'%{patron}%'])

            results = cursor.fetchall()
            for status1, status2, count in results:
                encontrados_level2.append((status1, status2, count))

        if encontrados_level2:
            print("4. ESTADOS CON 'UTIL' EN STATUS_LEVEL_2:")
            print("=" * 60)

            total_level2 = 0
            for status1, status2, count in encontrados_level2:
                print(f"   {status1} -> {status2}: {count}")
                total_level2 += count

            print(f"   TOTAL: {total_level2}")

        # 5. Verificar resultado_llamada
        print()
        print("5. VERIFICACION EN RESULTADO_LLAMADA:")
        print("=" * 60)

        cursor.execute("""
            SELECT resultado_llamada, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND resultado_llamada IS NOT NULL
            GROUP BY resultado_llamada
            ORDER BY count DESC
        """, [origen_archivo])

        resultados = cursor.fetchall()

        for resultado, count in resultados:
            print(f"   '{resultado}': {count}")

        # 6. Buscar exactamente 28 leads
        print()
        print("6. BUSCAR COMBINACIONES QUE SUMEN 28:")
        print("=" * 60)

        # Probar diferentes combinaciones
        combinaciones_28 = []

        for status, count in all_status:
            if count == 28:
                combinaciones_28.append(f"'{status}' = {count}")

        # Buscar sumas de dos estados
        for i, (status1, count1) in enumerate(all_status):
            for j, (status2, count2) in enumerate(all_status[i+1:], i+1):
                if count1 + count2 == 28:
                    combinaciones_28.append(f"'{status1}' + '{status2}' = {count1} + {count2} = 28")

        if combinaciones_28:
            print("   Combinaciones que suman 28:")
            for combo in combinaciones_28:
                print(f"     {combo}")
        else:
            print("   No se encontraron combinaciones que sumen exactamente 28")

        print()
        print("=" * 60)
        print("CONCLUSION:")
        print("Si ves '28 utiles positivos', puede ser:")
        print("1. Un conteo desde otra fuente (no esta BD)")
        print("2. Una suma de varios estados diferentes")
        print("3. Un conteo que incluye campos diferentes")
        print("4. Cache o datos no actualizados")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    buscar_utiles()
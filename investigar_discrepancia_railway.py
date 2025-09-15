#!/usr/bin/env python3
"""
Investiga la discrepancia entre utiles positivos y citas agendadas en Railway
"""

import pymysql
from datetime import datetime, date

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

def investigar_discrepancia():
    """Investiga la discrepancia entre utiles positivos y citas agendadas"""

    print("=== INVESTIGACION DISCREPANCIA RAILWAY ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Contar todos los status_level_1 existentes
        print("1. DISTRIBUCION COMPLETA DE STATUS_LEVEL_1:")
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            GROUP BY status_level_1
            ORDER BY count DESC
        """)
        status_dist = cursor.fetchall()

        total_segurcaixa = 0
        for status, count in status_dist:
            status_str = status if status else 'NULL'
            print(f"   {status_str}: {count}")
            total_segurcaixa += count

        print(f"   TOTAL SEGURCAIXA_JULIO: {total_segurcaixa}")
        print()

        # 2. Analisis detallado de "utiles positivos" vs "Cita Agendada"
        print("2. ANALISIS DETALLADO:")

        # Buscar variaciones del nombre
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND (status_level_1 LIKE '%util%' OR status_level_1 LIKE '%positiv%' OR status_level_1 LIKE '%Util%' OR status_level_1 LIKE '%Positiv%')
            GROUP BY status_level_1
            ORDER BY count DESC
        """)
        utiles = cursor.fetchall()

        print("   Leads con 'util/positiv' en status_level_1:")
        for status, count in utiles:
            print(f"     '{status}': {count}")

        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND (status_level_1 LIKE '%cita%' OR status_level_1 LIKE '%agenda%' OR status_level_1 LIKE '%Cita%' OR status_level_1 LIKE '%Agenda%')
            GROUP BY status_level_1
            ORDER BY count DESC
        """)
        citas = cursor.fetchall()

        print("   Leads con 'cita/agenda' en status_level_1:")
        for status, count in citas:
            print(f"     '{status}': {count}")

        print()

        # 3. Verificar si hay leads con citas programadas reales
        print("3. LEADS CON CITAS REALES (campo 'cita'):")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND cita IS NOT NULL
        """)
        con_cita = cursor.fetchone()[0]
        print(f"   Leads con campo 'cita' no NULL: {con_cita}")

        if con_cita > 0:
            cursor.execute("""
                SELECT status_level_1, cita, hora_cita, COUNT(*) as count
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND cita IS NOT NULL
                GROUP BY status_level_1, cita, hora_cita
                ORDER BY count DESC
                LIMIT 10
            """)
            ejemplos_cita = cursor.fetchall()

            print("   Ejemplos de leads con citas:")
            for status1, cita, hora, count in ejemplos_cita:
                print(f"     {count}x - status: '{status1}', cita: {cita}, hora: {hora}")

        print()

        # 4. Verificar status_level_2 para mas detalles
        print("4. DISTRIBUCION DE STATUS_LEVEL_2:")

        cursor.execute("""
            SELECT status_level_2, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_2 IS NOT NULL
            GROUP BY status_level_2
            ORDER BY count DESC
            LIMIT 15
        """)
        status2_dist = cursor.fetchall()

        for status2, count in status2_dist:
            print(f"   '{status2}': {count}")

        print()

        # 5. Buscar leads especificos que puedan causar la discrepancia
        print("5. BUSQUEDA DE LEADS PROBLEMATICOS:")

        # Leads con status contradictorio
        cursor.execute("""
            SELECT id, nombre, telefono, status_level_1, status_level_2, cita, resultado_llamada
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND (
                (status_level_1 LIKE '%Cita%' AND cita IS NULL) OR
                (status_level_1 NOT LIKE '%Cita%' AND cita IS NOT NULL) OR
                (status_level_1 LIKE '%util%' AND status_level_2 NOT LIKE '%cita%')
            )
            LIMIT 10
        """)
        problematicos = cursor.fetchall()

        if problematicos:
            print("   Leads con estados contradictorios:")
            for id, nombre, tel, status1, status2, cita, resultado in problematicos:
                cita_str = str(cita) if cita else 'NULL'
                resultado_str = resultado if resultado else 'NULL'
                print(f"     Lead {id}: {nombre}")
                print(f"       status_level_1: '{status1}'")
                print(f"       status_level_2: '{status2}'")
                print(f"       cita: {cita_str}")
                print(f"       resultado_llamada: {resultado_str}")
                print()
        else:
            print("   No se encontraron leads con estados contradictorios")

        # 6. Verificar leads modificados recientemente
        print("6. LEADS MODIFICADOS RECIENTEMENTE (ultimas 24h):")

        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND updated_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY status_level_1
            ORDER BY count DESC
        """)
        recientes = cursor.fetchall()

        if recientes:
            print("   Status de leads modificados en 24h:")
            for status, count in recientes:
                status_str = status if status else 'NULL'
                print(f"     {status_str}: {count}")
        else:
            print("   No hay leads modificados en las ultimas 24h")

        print()

        # 7. Conteo final para verificar
        print("7. CONTEO FINAL DE VERIFICACION:")

        cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO' AND status_level_1 = 'Cita Agendada'")
        cita_agendada = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO' AND status_level_1 LIKE '%til%'")
        util_count = cursor.fetchone()[0]

        print(f"   'Cita Agendada': {cita_agendada}")
        print(f"   Con 'til' (utiles): {util_count}")
        print()

        # 8. Mostrar los datos exactos que causan confusion
        if cita_agendada > 0:
            print("8. DETALLES DE LEADS CON 'Cita Agendada':")
            cursor.execute("""
                SELECT id, nombre, telefono, status_level_2, cita, hora_cita, updated_at
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND status_level_1 = 'Cita Agendada'
                ORDER BY updated_at DESC
            """)
            detalles_cita = cursor.fetchall()

            for id, nombre, tel, status2, cita, hora, updated in detalles_cita:
                print(f"   Lead {id}: {nombre} ({tel})")
                print(f"     status_level_2: {status2}")
                print(f"     cita: {cita}, hora: {hora}")
                print(f"     updated_at: {updated}")
                print()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    investigar_discrepancia()
    print()
    print("=" * 60)
    print("INVESTIGACION COMPLETADA")
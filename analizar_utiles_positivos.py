#!/usr/bin/env python3
"""
Analiza la discrepancia entre 28 utiles positivos y 9 citas agendadas
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

def analizar_discrepancia():
    """Analiza por que hay 28 utiles positivos pero solo 9 citas agendadas"""

    print("=== ANALISIS UTILES POSITIVOS vs CITAS AGENDADAS ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        origen_archivo = 'SEGURCAIXA_JULIO'

        # 1. Buscar todas las variaciones de "utiles positivos"
        print("1. BUSQUEDA DE TODOS LOS 'UTILES POSITIVOS':")
        print("=" * 60)

        # Buscar todos los status que contengan "util" o "positiv"
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (
                status_level_1 LIKE '%%util%%' OR
                status_level_1 LIKE '%%positiv%%' OR
                status_level_1 LIKE '%%Util%%' OR
                status_level_1 LIKE '%%Positiv%%'
            )
            GROUP BY status_level_1
            ORDER BY count DESC
        """, [origen_archivo])

        utiles_results = cursor.fetchall()
        total_utiles = 0

        for status, count in utiles_results:
            print(f"   '{status}': {count} leads")
            total_utiles += count

        print(f"   TOTAL UTILES: {total_utiles}")
        print()

        # 2. Contar exactamente las "Cita Agendada"
        print("2. CONTEO DE 'CITA AGENDADA':")
        print("=" * 60)

        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = %s AND status_level_1 = 'Cita Agendada'
        """, [origen_archivo])

        citas_agendadas = cursor.fetchone()[0]
        print(f"   'Cita Agendada': {citas_agendadas} leads")
        print()

        # 3. Analizar detalladamente los "utiles positivos"
        print("3. DETALLES DE CADA TIPO DE 'UTIL/POSITIV':")
        print("=" * 60)

        for status, count in utiles_results:
            print(f"\n   ANALIZANDO '{status}' ({count} leads):")

            # Mostrar algunos ejemplos
            cursor.execute("""
                SELECT id, nombre, telefono, status_level_2, cita, fecha_minima_reserva, updated_at
                FROM leads
                WHERE origen_archivo = %s AND status_level_1 = %s
                ORDER BY updated_at DESC
                LIMIT 5
            """, [origen_archivo, status])

            ejemplos = cursor.fetchall()

            for id, nombre, tel, status2, cita, fecha_min, updated in ejemplos:
                print(f"     Lead {id}: {nombre} ({tel})")
                print(f"       status_level_2: {status2}")
                print(f"       cita: {cita}")
                print(f"       fecha_minima_reserva: {fecha_min}")
                print(f"       updated_at: {updated}")
                print()

        # 4. Verificar si algunos "utiles" deberian ser "Cita Agendada"
        print("4. VERIFICACION DE CRITERIOS PARA 'CITA AGENDADA':")
        print("=" * 60)

        # Utiles con cita real
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (
                status_level_1 LIKE '%%util%%' OR
                status_level_1 LIKE '%%positiv%%' OR
                status_level_1 LIKE '%%Util%%' OR
                status_level_1 LIKE '%%Positiv%%'
            )
            AND cita IS NOT NULL
            GROUP BY status_level_1
        """, [origen_archivo])

        utiles_con_cita = cursor.fetchall()
        if utiles_con_cita:
            print("   'Utiles' con cita real (deberian ser 'Cita Agendada'):")
            for status, count in utiles_con_cita:
                print(f"     '{status}': {count} leads")

        # Utiles con fecha_minima_reserva
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (
                status_level_1 LIKE '%%util%%' OR
                status_level_1 LIKE '%%positiv%%' OR
                status_level_1 LIKE '%%Util%%' OR
                status_level_1 LIKE '%%Positiv%%'
            )
            AND fecha_minima_reserva IS NOT NULL
            GROUP BY status_level_1
        """, [origen_archivo])

        utiles_con_fecha = cursor.fetchall()
        if utiles_con_fecha:
            print("   'Utiles' con fecha_minima_reserva (deberian ser 'Cita Agendada'):")
            for status, count in utiles_con_fecha:
                print(f"     '{status}': {count} leads")

        print()

        # 5. Contar cuantos "utiles" no tienen cita ni fecha_minima
        print("5. UTILES SIN CITA NI FECHA_MINIMA:")
        print("=" * 60)

        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (
                status_level_1 LIKE '%%util%%' OR
                status_level_1 LIKE '%%positiv%%' OR
                status_level_1 LIKE '%%Util%%' OR
                status_level_1 LIKE '%%Positiv%%'
            )
            AND cita IS NULL
            AND fecha_minima_reserva IS NULL
            GROUP BY status_level_1
        """, [origen_archivo])

        utiles_sin_cita_fecha = cursor.fetchall()
        total_sin_justificacion = 0

        if utiles_sin_cita_fecha:
            print("   'Utiles' SIN cita ni fecha_minima (estos estan correctos):")
            for status, count in utiles_sin_cita_fecha:
                print(f"     '{status}': {count} leads")
                total_sin_justificacion += count

        print()

        # 6. Resumen y explicacion
        print("6. EXPLICACION DE LA DISCREPANCIA:")
        print("=" * 60)

        print(f"   Total 'utiles positivos': {total_utiles}")
        print(f"   Total 'Cita Agendada': {citas_agendadas}")
        print(f"   Diferencia: {total_utiles - citas_agendadas}")
        print()

        print("   POSIBLES EXPLICACIONES:")
        print("   - Algunos 'utiles' tienen cita/fecha_minima y deberian ser 'Cita Agendada'")
        print("   - Los 'utiles' sin cita son leads que estan interesados pero sin cita confirmada")
        print("   - Puede haber diferentes tipos de 'util' (ej: 'util positivo', 'util interesado', etc)")

        return {
            'total_utiles': total_utiles,
            'citas_agendadas': citas_agendadas,
            'diferencia': total_utiles - citas_agendadas
        }

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    resultado = analizar_discrepancia()
    if resultado:
        print()
        print("=" * 60)
        print("ANALISIS COMPLETADO")
        print(f"La diferencia de {resultado['diferencia']} se debe a leads 'utiles'")
        print("que no tienen cita programada pero estan interesados")
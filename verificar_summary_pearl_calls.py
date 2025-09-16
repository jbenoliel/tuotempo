#!/usr/bin/env python3
"""
Verifica el estado del campo summary en pearl_calls y como recuperarlo
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

def verificar_summary():
    """Verifica el estado de los summaries en pearl_calls"""

    print("=== VERIFICACION SUMMARY EN PEARL_CALLS ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Estructura de la tabla pearl_calls
        print("1. ESTRUCTURA DE TABLA PEARL_CALLS:")
        print("=" * 60)

        cursor.execute("DESCRIBE pearl_calls")
        columns = cursor.fetchall()

        for column in columns:
            print(f"   {column[0]} - {column[1]} - {column[2]} - {column[3]}")

        print()

        # 2. Contar registros con y sin summary
        print("2. ESTADO DEL CAMPO SUMMARY:")
        print("=" * 60)

        cursor.execute("SELECT COUNT(*) FROM pearl_calls")
        total_calls = cursor.fetchone()[0]
        print(f"   Total registros en pearl_calls: {total_calls}")

        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        con_summary = cursor.fetchone()[0]
        print(f"   Registros CON summary: {con_summary}")

        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NULL OR summary = ''")
        sin_summary = cursor.fetchone()[0]
        print(f"   Registros SIN summary: {sin_summary}")

        print()

        # 3. Verificar registros con call_id pero sin summary
        print("3. REGISTROS CON CALL_ID PERO SIN SUMMARY:")
        print("=" * 60)

        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
        """)
        con_call_id_sin_summary = cursor.fetchone()[0]
        print(f"   Registros con call_id pero sin summary: {con_call_id_sin_summary}")

        if con_call_id_sin_summary > 0:
            print("   [PROBLEMA IDENTIFICADO] Hay llamadas con call_id pero sin summary")
            print("   Estos se pueden recuperar de Pearl AI usando el call_id")

            # Mostrar algunos ejemplos
            cursor.execute("""
                SELECT id, lead_id, call_id, status, created_at
                FROM pearl_calls
                WHERE call_id IS NOT NULL AND call_id != ''
                AND (summary IS NULL OR summary = '')
                ORDER BY created_at DESC
                LIMIT 5
            """)
            ejemplos = cursor.fetchall()

            print()
            print("   EJEMPLOS DE LLAMADAS SIN SUMMARY:")
            for id, lead_id, call_id, status, created_at in ejemplos:
                print(f"     ID: {id} | Lead: {lead_id} | Call_ID: {call_id}")
                print(f"       Status: {status} | Fecha: {created_at}")

        print()

        # 4. Verificar registros recientes
        print("4. REGISTROS RECIENTES (ultimas 10):")
        print("=" * 60)

        cursor.execute("""
            SELECT id, lead_id, call_id, status, summary, created_at
            FROM pearl_calls
            ORDER BY created_at DESC
            LIMIT 10
        """)
        recientes = cursor.fetchall()

        for id, lead_id, call_id, status, summary, created_at in recientes:
            summary_status = "CON SUMMARY" if summary else "SIN SUMMARY"
            call_id_status = call_id if call_id else "SIN CALL_ID"
            print(f"   ID {id}: Lead {lead_id} | {call_id_status}")
            print(f"     Status: {status} | {summary_status}")
            print(f"     Fecha: {created_at}")
            if summary:
                print(f"     Summary: {summary[:100]}...")
            print()

        # 5. Analizar el patron
        print("5. ANALISIS DEL PATRON:")
        print("=" * 60)

        # Verificar si hay diferencias por status
        cursor.execute("""
            SELECT status,
                   COUNT(*) as total,
                   SUM(CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END) as con_summary,
                   SUM(CASE WHEN call_id IS NOT NULL AND call_id != '' THEN 1 ELSE 0 END) as con_call_id
            FROM pearl_calls
            GROUP BY status
            ORDER BY total DESC
        """)
        por_status = cursor.fetchall()

        print("   Por status:")
        for status, total, con_summary, con_call_id in por_status:
            print(f"     {status}: {total} total, {con_summary} con summary, {con_call_id} con call_id")

        return {
            'total': total_calls,
            'con_summary': con_summary,
            'sin_summary': sin_summary,
            'recuperables': con_call_id_sin_summary
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
    resultado = verificar_summary()
    if resultado:
        print()
        print("=" * 60)
        print("RESUMEN:")
        print(f"  Total llamadas: {resultado['total']}")
        print(f"  Con summary: {resultado['con_summary']}")
        print(f"  Sin summary: {resultado['sin_summary']}")
        print(f"  Recuperables (con call_id): {resultado['recuperables']}")

        if resultado['recuperables'] > 0:
            print()
            print("[ACCION NECESARIA]")
            print(f"Se pueden recuperar {resultado['recuperables']} summaries")
            print("usando el call_id de Pearl AI")
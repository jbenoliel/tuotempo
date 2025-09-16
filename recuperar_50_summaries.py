#!/usr/bin/env python3
"""
Recupera 50 summaries por ejecucion para evitar timeouts
"""

import pymysql
from datetime import datetime
from pearl_caller import get_pearl_client

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

def recuperar_50_summaries():
    """Recupera exactamente 50 summaries"""

    print(f"=== RECUPERANDO 50 SUMMARIES - {datetime.now().strftime('%H:%M:%S')} ===")

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Estado inicial
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        inicial = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
        """)
        pendientes = cursor.fetchone()[0]

        print(f"Summaries actuales: {inicial}")
        print(f"Pendientes (status=4): {pendientes}")

        if pendientes == 0:
            print("[COMPLETADO] No hay mas summaries para recuperar")
            return inicial

        # Obtener 50 registros
        cursor.execute("""
            SELECT id, call_id, lead_id
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
            ORDER BY created_at DESC
            LIMIT 50
        """)

        registros = cursor.fetchall()
        print(f"Procesando {len(registros)} registros...")

        client = get_pearl_client()
        recuperados = 0

        for i, (id_registro, call_id, lead_id) in enumerate(registros, 1):
            try:
                call_details = client.get_call_status(call_id)

                if call_details:
                    summary = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')

                    if summary and summary.strip():
                        cursor.execute("""
                            UPDATE pearl_calls
                            SET summary = %s, updated_at = NOW()
                            WHERE id = %s
                        """, [summary, id_registro])

                        recuperados += 1

                        if i % 10 == 0:
                            print(f"  Procesados: {i}/50 - Recuperados: {recuperados}")

            except Exception as e:
                continue

        conn.commit()

        # Estado final
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        final = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
        """)
        pendientes_final = cursor.fetchone()[0]

        print(f"\nRESULTADOS:")
        print(f"  Summaries recuperados: {recuperados}")
        print(f"  Total summaries: {inicial} -> {final} (+{final - inicial})")
        print(f"  Pendientes: {pendientes} -> {pendientes_final}")

        if pendientes_final > 0:
            print(f"\n[CONTINUAR] Ejecuta de nuevo para recuperar {pendientes_final} mas")
        else:
            print(f"\n[COMPLETADO] Todos los summaries han sido recuperados!")

        return final

    except Exception as e:
        print(f"ERROR: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    recuperar_50_summaries()
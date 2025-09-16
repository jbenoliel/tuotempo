#!/usr/bin/env python3
"""
Recuperacion automatica de summaries en multiples lotes
"""

import pymysql
from datetime import datetime
from pearl_caller import get_pearl_client
import time

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

def recuperar_lote(client, cursor, conn, lote_num):
    """Recupera un lote de 50 summaries"""

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

    if not registros:
        return 0, 0  # No hay más registros

    recuperados = 0

    for id_registro, call_id, lead_id in registros:
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

        except Exception as e:
            continue

    conn.commit()
    return len(registros), recuperados

def recuperacion_automatica():
    """Ejecuta recuperacion automatica de summaries"""

    print("=== RECUPERACION AUTOMATICA DE SUMMARIES ===")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print()

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
        total_pendientes = cursor.fetchone()[0]

        print(f"Estado inicial:")
        print(f"  Summaries existentes: {inicial}")
        print(f"  Pendientes de recuperar: {total_pendientes}")
        print()

        if total_pendientes == 0:
            print("[COMPLETADO] No hay summaries para recuperar")
            return

        # Conectar a Pearl
        client = get_pearl_client()

        # Procesar hasta 10 lotes (500 registros máximo)
        max_lotes = min(10, (total_pendientes + 49) // 50)
        total_procesados = 0
        total_recuperados = 0

        print(f"Procesando hasta {max_lotes} lotes (50 registros cada uno)...")
        print()

        for lote in range(1, max_lotes + 1):
            print(f"LOTE {lote}/{max_lotes} - {datetime.now().strftime('%H:%M:%S')}")

            procesados, recuperados = recuperar_lote(client, cursor, conn, lote)

            if procesados == 0:
                print("  No hay más registros para procesar")
                break

            total_procesados += procesados
            total_recuperados += recuperados

            print(f"  Procesados: {procesados}, Recuperados: {recuperados}")

            # Breve pausa entre lotes
            time.sleep(1)

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

        print()
        print("RESUMEN FINAL:")
        print(f"  Lotes procesados: {lote}")
        print(f"  Registros procesados: {total_procesados}")
        print(f"  Summaries recuperados: {total_recuperados}")
        print(f"  Total summaries: {inicial} -> {final} (+{final - inicial})")
        print(f"  Pendientes: {total_pendientes} -> {pendientes_final}")

        if pendientes_final > 0:
            print()
            print(f"[INFO] Quedan {pendientes_final} summaries pendientes")
            print("Ejecuta el script de nuevo para continuar")
        else:
            print()
            print("[COMPLETADO] Todos los summaries disponibles han sido recuperados!")

        return final - inicial

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    resultado = recuperacion_automatica()
    print()
    print(f"Summaries recuperados en esta ejecución: {resultado}")
    print(f"Completado: {datetime.now().strftime('%H:%M:%S')}")
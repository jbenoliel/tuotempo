#!/usr/bin/env python3
"""
Recuperacion rapida de summaries con progreso en tiempo real
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

def recuperar_summaries_lote():
    """Recupera summaries en lotes pequenos con feedback continuo"""

    print(f"=== RECUPERACION RAPIDA SUMMARIES - {datetime.now().strftime('%H:%M:%S')} ===")

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
        total_recuperables = cursor.fetchone()[0]

        print(f"Summaries actuales: {inicial}")
        print(f"Recuperables (status=4): {total_recuperables}")

        if total_recuperables == 0:
            print("No hay summaries para recuperar")
            return inicial

        # Procesar en lotes de 100
        lote_size = 100
        client = get_pearl_client()
        total_recuperados = 0

        for lote in range(0, min(500, total_recuperables), lote_size):  # Maximo 500 por ejecucion
            print(f"\nLOTE {lote//lote_size + 1} - Registros {lote+1}-{min(lote+lote_size, total_recuperables)}")

            # Obtener lote actual
            cursor.execute("""
                SELECT id, call_id, lead_id
                FROM pearl_calls
                WHERE call_id IS NOT NULL AND call_id != ''
                AND (summary IS NULL OR summary = '')
                AND status = '4'
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, [lote_size, lote])

            registros = cursor.fetchall()

            if not registros:
                break

            recuperados_lote = 0

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

                            recuperados_lote += 1

                except Exception as e:
                    continue

            # Commit del lote
            conn.commit()
            total_recuperados += recuperados_lote

            print(f"  Recuperados en este lote: {recuperados_lote}")
            print(f"  Total recuperados: {total_recuperados}")

            # Mostrar algunos ejemplos
            if recuperados_lote > 0:
                cursor.execute("""
                    SELECT summary FROM pearl_calls
                    WHERE summary IS NOT NULL AND summary != ''
                    ORDER BY updated_at DESC
                    LIMIT 1
                """)
                ultimo_summary = cursor.fetchone()
                if ultimo_summary:
                    preview = ultimo_summary[0][:80] + "..."
                    print(f"  Ultimo summary: {preview}")

        # Estado final
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        final = cursor.fetchone()[0]

        print(f"\nRESUMEN:")
        print(f"  Summaries antes: {inicial}")
        print(f"  Summaries ahora: {final}")
        print(f"  Nuevos recuperados: {final - inicial}")

        return final

    except Exception as e:
        print(f"ERROR: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    resultado = recuperar_summaries_lote()
    print(f"\n[COMPLETADO] Total summaries en BD: {resultado}")
#!/usr/bin/env python3
"""
Recupera summaries empezando por los registros MAS ANTIGUOS
donde es mas probable que Pearl haya generado summaries
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

def recuperar_antiguos():
    """Recupera summaries empezando por los mas antiguos"""

    print(f"=== RECUPERANDO SUMMARIES ANTIGUOS - {datetime.now().strftime('%H:%M:%S')} ===")

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Estado inicial
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        inicial = cursor.fetchone()[0]

        # Obtener registros ANTIGUOS PRIMERO (orden ASC)
        cursor.execute("""
            SELECT id, call_id, lead_id, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
            ORDER BY created_at ASC
            LIMIT 100
        """)

        registros = cursor.fetchall()
        print(f"Procesando {len(registros)} registros MAS ANTIGUOS...")

        if len(registros) == 0:
            print("No hay registros antiguos para procesar")
            return inicial

        # Mostrar rango de fechas
        fecha_inicio = registros[0][3]
        fecha_fin = registros[-1][3]
        print(f"Rango de fechas: {fecha_inicio} a {fecha_fin}")
        print()

        client = get_pearl_client()
        recuperados = 0

        for i, (id_registro, call_id, lead_id, created_at) in enumerate(registros, 1):
            try:
                call_details = client.get_call_status(call_id)

                if call_details:
                    summary = call_details.get('summary', {}.get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary'))

                    if summary and summary.strip():
                        cursor.execute("""
                            UPDATE pearl_calls
                            SET summary = %s, updated_at = NOW()
                            WHERE id = %s
                        """, [summary, id_registro])

                        recuperados += 1

                        if recuperados % 5 == 0:
                            print(f"  Recuperados: {recuperados} (procesando {i}/{len(registros)})")

                        # Commit cada 10 recuperaciones
                        if recuperados % 10 == 0:
                            conn.commit()

            except Exception as e:
                continue

        # Commit final
        conn.commit()

        # Estado final
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        final = cursor.fetchone()[0]

        print(f"\nRESULTADOS:")
        print(f"  Registros procesados: {len(registros)}")
        print(f"  Summaries recuperados: {recuperados}")
        print(f"  Total summaries: {inicial} -> {final} (+{final - inicial})")

        if recuperados > 0:
            # Mostrar ejemplo del último recuperado
            cursor.execute("""
                SELECT summary FROM pearl_calls
                WHERE summary IS NOT NULL AND summary != ''
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            ultimo = cursor.fetchone()
            if ultimo:
                preview = ultimo[0][:100] + "..."
                print(f"  Ejemplo: {preview}")

        return final

    except Exception as e:
        print(f"ERROR: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    resultado = recuperar_antiguos()
    print(f"\nTotal summaries en BD: {resultado}")
#!/usr/bin/env python3
"""
Limpia los call_ids sintéticos generados por error
"""

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_railway_connection():
    config = {
        'host': 'ballast.proxy.rlwy.net',
        'port': 11616,
        'user': 'root',
        'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        'database': 'railway',
        'ssl_disabled': True,
        'autocommit': True,
        'charset': 'utf8mb4'
    }
    try:
        return mysql.connector.connect(**config)
    except Exception as e:
        print(f"Error: {e}")
        return None

def limpiar_callids_sinteticos():
    conn = get_railway_connection()
    if not conn:
        return

    cursor = conn.cursor()

    print("LIMPIEZA DE CALL_IDS SINTÉTICOS")
    print("=" * 50)

    # 1. Contar registros a eliminar
    cursor.execute("""
        SELECT COUNT(*)
        FROM pearl_calls
        WHERE call_id LIKE '68cacf%'
        AND status = 'invalid_call_id'
    """)

    count_to_delete = cursor.fetchone()[0]
    print(f"Call_ids sintéticos encontrados: {count_to_delete}")

    if count_to_delete == 0:
        print("No hay call_ids sintéticos que limpiar.")
        cursor.close()
        conn.close()
        return

    # 2. Mostrar algunos ejemplos
    cursor.execute("""
        SELECT call_id, lead_id, created_at
        FROM pearl_calls
        WHERE call_id LIKE '68cacf%'
        AND status = 'invalid_call_id'
        ORDER BY created_at
        LIMIT 5
    """)

    ejemplos = cursor.fetchall()
    print(f"\nEjemplos a eliminar:")
    for call_id, lead_id, created in ejemplos:
        print(f"  {call_id} (Lead: {lead_id}, Creado: {created})")

    # 3. Proceder automáticamente (son registros inválidos sintéticos)
    print(f"\nProcediendo a eliminar registros sintéticos inválidos...")

    # 4. Eliminar registros sintéticos
    print(f"\nEliminando {count_to_delete} call_ids sintéticos...")

    cursor.execute("""
        DELETE FROM pearl_calls
        WHERE call_id LIKE '68cacf%'
        AND status = 'invalid_call_id'
    """)

    eliminados = cursor.rowcount
    print(f"OK - Eliminados {eliminados} call_ids sinteticos")

    # 5. Verificación final
    cursor.execute("""
        SELECT COUNT(*)
        FROM pearl_calls
        WHERE call_id LIKE '68cacf%'
    """)

    restantes = cursor.fetchone()[0]
    print(f"Call_ids con patrón 68cacf restantes: {restantes}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    limpiar_callids_sinteticos()
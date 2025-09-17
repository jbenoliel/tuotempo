#!/usr/bin/env python3
"""
Verificar estado de call_ids invalidos
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

def check_invalid_calls():
    conn = get_railway_connection()
    if not conn:
        return

    cursor = conn.cursor()

    # Contar call_ids inválidos
    cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE status = 'invalid_call_id'")
    invalid_count = cursor.fetchone()[0]

    # Contar llamadas válidas con resumen
    cursor.execute("""
        SELECT COUNT(*) FROM pearl_calls
        WHERE summary IS NOT NULL
        AND summary != ''
        AND summary != 'Call_id invalido - no reconocido por Pearl AI'
    """)
    valid_count = cursor.fetchone()[0]

    # Total de registros
    cursor.execute("SELECT COUNT(*) FROM pearl_calls")
    total_count = cursor.fetchone()[0]

    print("ESTADO DE CALL_IDS")
    print("=" * 40)
    print(f"Call IDs invalidos marcados: {invalid_count}")
    print(f"Llamadas con resumen valido: {valid_count}")
    print(f"Total registros pearl_calls: {total_count}")
    print(f"Porcentaje validas: {(valid_count/total_count*100):.1f}%" if total_count > 0 else "N/A")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_invalid_calls()
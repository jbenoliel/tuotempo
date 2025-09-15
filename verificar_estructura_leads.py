#!/usr/bin/env python3
"""
Verifica la estructura de la tabla leads en Railway
"""

import pymysql

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

def verificar_estructura():
    """Verifica la estructura de la tabla leads"""

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Ver estructura de la tabla leads
        print("=== ESTRUCTURA DE LA TABLA LEADS ===")
        cursor.execute("DESCRIBE leads")
        columnas = cursor.fetchall()

        print("Columnas disponibles:")
        for columna in columnas:
            field, tipo, null, key, default, extra = columna
            print(f"  {field}: {tipo} (null={null}, key={key})")

        print()

        # Verificar leads problematicos con columnas correctas
        print("=== VERIFICACION LEADS PROBLEMATICOS ===")
        leads_problematicos = [2407, 2399, 2133, 2422, 2000]

        for lead_id in leads_problematicos:
            cursor.execute("""
                SELECT id, lead_status, status_level_1,
                       call_attempts_count, call_status, telefono, nombre
                FROM leads
                WHERE id = %s
            """, (lead_id,))

            lead = cursor.fetchone()
            if lead:
                id, lead_status, status_level_1, attempts, call_status, telefono, nombre = lead
                print(f"Lead {id}: {lead_status}, {status_level_1}, intentos={attempts}, call_status={call_status}")
            else:
                print(f"Lead {lead_id}: NO EXISTE")

        print()

        # Verificar conteo de 'Volver a llamar'
        print("=== CONTEO VOLVER A LLAMAR ===")
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE status_level_1 = 'Volver a llamar'
        """)
        total = cursor.fetchone()[0]
        print(f"Total con 'Volver a llamar': {total}")

        cursor.execute("""
            SELECT lead_status, COUNT(*) as count
            FROM leads
            WHERE status_level_1 = 'Volver a llamar'
            GROUP BY lead_status
        """)
        distribucion = cursor.fetchall()
        print("Distribucion por lead_status:")
        for status, count in distribucion:
            print(f"  {status}: {count}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    verificar_estructura()
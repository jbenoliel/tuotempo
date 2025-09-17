#!/usr/bin/env python3
"""
Script para verificar call_ids en la tabla pearl_calls
"""

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_railway_connection():
    """Conexión directa a Railway"""
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
        conn = mysql.connector.connect(**config)
        return conn
    except Exception as e:
        print(f"Error conectando a Railway: {e}")
        return None

def verificar_callids():
    """Verificar call_ids disponibles para leads interesados"""
    try:
        conn = get_railway_connection()
        if conn is None:
            return

        cursor = conn.cursor()

        # Verificar call_ids de leads interesados sin cita
        query = """
        SELECT l.id, l.nombre, l.apellidos, l.telefono,
               pc.call_id, pc.summary, pc.created_at
        FROM leads l
        INNER JOIN pearl_calls pc ON l.id = pc.lead_id
        WHERE l.fecha_minima_reserva IS NOT NULL
        AND l.cita IS NULL
        AND pc.call_id IS NOT NULL
        AND pc.call_id != ''
        ORDER BY l.nombre, pc.created_at DESC
        LIMIT 10
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print("CALL_IDS DISPONIBLES PARA LEADS INTERESADOS SIN CITA")
        print("=" * 70)

        if results:
            for row in results:
                lead_id, nombre, apellidos, telefono, call_id, summary, created_at = row
                print(f"\nLead ID: {lead_id}")
                print(f"Nombre: {nombre} {apellidos or ''}")
                print(f"Teléfono: {telefono}")
                print(f"Call ID: {call_id}")
                print(f"Fecha: {created_at}")
                print(f"Resumen: {summary[:100] if summary else 'SIN RESUMEN'}...")
                print("-" * 50)

            # Contar total
            cursor.execute("""
                SELECT COUNT(DISTINCT l.id)
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.fecha_minima_reserva IS NOT NULL
                AND l.cita IS NULL
                AND pc.call_id IS NOT NULL
                AND pc.call_id != ''
            """)
            total = cursor.fetchone()[0]
            print(f"\nTOTAL LEADS INTERESADOS CON CALL_ID: {total}")

        else:
            print("No se encontraron call_ids para leads interesados")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_callids()
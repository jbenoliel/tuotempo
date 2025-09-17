#!/usr/bin/env python3
"""
Script para verificar los resumenes de llamadas
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

def verificar_resumenes():
    """Verificar si hay resumenes de llamadas"""
    try:
        conn = get_railway_connection()
        if conn is None:
            return

        cursor = conn.cursor()

        # Verificar si hay resumenes en pearl_calls
        query = """
        SELECT pc.id, pc.phone_number, pc.lead_id, l.nombre, pc.summary, LENGTH(pc.summary) as resumen_length
        FROM pearl_calls pc
        LEFT JOIN leads l ON pc.lead_id = l.id
        WHERE pc.summary IS NOT NULL AND pc.summary != ''
        AND l.fecha_minima_reserva IS NOT NULL
        AND l.cita IS NULL
        ORDER BY pc.created_at DESC
        LIMIT 5
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print("VERIFICACIÓN DE RESUMENES DE LLAMADAS")
        print("=" * 60)

        if results:
            for row in results:
                pc_id, telefono, lead_id, nombre, summary, resumen_length = row
                print(f"\nPearl Call ID: {pc_id}")
                print(f"Lead ID: {lead_id}")
                print(f"Nombre: {nombre}")
                print(f"Teléfono: {telefono}")
                print(f"Longitud resumen: {resumen_length}")
                print(f"Resumen: {summary[:200] if summary else 'SIN RESUMEN'}...")
                print("-" * 40)
        else:
            print("No se encontraron resumenes en pearl_calls")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_resumenes()
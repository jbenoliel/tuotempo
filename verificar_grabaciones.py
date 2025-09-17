#!/usr/bin/env python3
"""
Script para verificar qué datos de grabaciones tenemos
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

def verificar_grabaciones():
    """Verificar qué campos de grabación tenemos"""
    try:
        conn = get_railway_connection()
        if conn is None:
            return

        cursor = conn.cursor()

        # Verificar campos en pearl_calls
        print("=== VERIFICANDO CAMPOS EN PEARL_CALLS ===")
        cursor.execute("DESCRIBE pearl_calls")
        fields = cursor.fetchall()

        recording_fields = []
        for field in fields:
            field_name = field[0]
            if 'record' in field_name.lower() or 'url' in field_name.lower():
                recording_fields.append(field_name)
                print(f"Campo relacionado con grabación: {field_name}")

        # Verificar datos de grabaciones
        print("\n=== VERIFICANDO DATOS DE GRABACIONES ===")
        for field in recording_fields:
            cursor.execute(f"SELECT COUNT(*) FROM pearl_calls WHERE {field} IS NOT NULL AND {field} != ''")
            count = cursor.fetchone()[0]
            print(f"Registros con {field}: {count}")

        # Verificar campos en leads
        print("\n=== VERIFICANDO CAMPOS EN LEADS ===")
        cursor.execute("DESCRIBE leads")
        fields = cursor.fetchall()

        recording_fields_leads = []
        for field in fields:
            field_name = field[0]
            if 'record' in field_name.lower() or 'url' in field_name.lower():
                recording_fields_leads.append(field_name)
                print(f"Campo relacionado con grabación: {field_name}")

        for field in recording_fields_leads:
            cursor.execute(f"SELECT COUNT(*) FROM leads WHERE {field} IS NOT NULL AND {field} != ''")
            count = cursor.fetchone()[0]
            print(f"Registros con {field}: {count}")

        # Mostrar algunos ejemplos de URLs si existen
        print("\n=== EJEMPLOS DE URLs DE GRABACIÓN ===")
        cursor.execute("""
            SELECT pc.recording_url, pc.call_id, l.nombre
            FROM pearl_calls pc
            LEFT JOIN leads l ON pc.lead_id = l.id
            WHERE pc.recording_url IS NOT NULL AND pc.recording_url != ''
            LIMIT 3
        """)
        examples = cursor.fetchall()

        for example in examples:
            url, call_id, nombre = example
            print(f"Nombre: {nombre}, Call ID: {call_id}")
            print(f"URL: {url[:100]}...")
            print("-" * 40)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_grabaciones()
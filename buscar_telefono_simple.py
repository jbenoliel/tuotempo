"""
Script simple para buscar un telefono en la BD
"""

import mysql.connector
import os
import re
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        DB_CONFIG = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'tuotempo'),
            'ssl_disabled': True,
            'autocommit': True,
            'charset': 'utf8mb4',
            'use_unicode': True
        }
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as e:
        print(f"Error conectando: {e}")
        return None

def normalizar_telefono(telefono):
    if not telefono:
        return ""
    telefono_digits = re.sub(r'\D', '', str(telefono))
    if len(telefono_digits) > 9:
        telefono_digits = telefono_digits[-9:]
    return telefono_digits

def buscar_telefono(telefono_original):
    print(f"=== BUSQUEDA DE TELEFONO ===")
    print(f"Telefono original: {telefono_original}")

    telefono_normalizado = normalizar_telefono(telefono_original)
    print(f"Telefono normalizado: {telefono_normalizado}")

    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor(dictionary=True)

        # Busqueda como hace la API
        print(f"\nBusqueda con REGEXP (como hace la API):")
        cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 5", (telefono_normalizado,))
        results = cursor.fetchall()

        if results:
            print(f"Encontrados {len(results)} leads:")
            for lead in results:
                print(f"  ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: {lead['telefono']} | Tel2: {lead['telefono2']}")
        else:
            print("No se encontraron leads")

        # Busqueda parcial
        print(f"\nBusqueda parcial (que contenga {telefono_normalizado}):")
        cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads WHERE telefono LIKE %s OR telefono2 LIKE %s LIMIT 10",
                      (f'%{telefono_normalizado}%', f'%{telefono_normalizado}%'))
        results2 = cursor.fetchall()

        if results2:
            print(f"Encontrados {len(results2)} leads con busqueda parcial:")
            for lead in results2:
                print(f"  ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: {lead['telefono']} | Tel2: {lead['telefono2']}")
        else:
            print("No se encontraron leads con busqueda parcial")

        # Estadisticas
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()['total']
        print(f"\nTotal leads en BD: {total}")

    except mysql.connector.Error as e:
        print(f"Error en consulta: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    import sys

    telefono = "+34629203315"
    if len(sys.argv) > 1:
        telefono = sys.argv[1]

    buscar_telefono(telefono)
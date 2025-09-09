#!/usr/bin/env python3
"""
Verificar que el teléfono 613523714 existe en Railway
"""

import mysql.connector
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()

def get_railway_connection():
    mysql_url = os.getenv('MYSQL_URL')
    url = urlparse(mysql_url)
    config = {
        'host': url.hostname,
        'port': url.port or 3306,
        'user': url.username,
        'password': url.password,
        'database': url.path[1:]
    }
    return mysql.connector.connect(**config)

def verificar_telefono():
    connection = None
    try:
        connection = get_railway_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Buscar el teléfono específico
        cursor.execute("""
            SELECT nombre, apellidos, telefono, telefono2, origen_archivo 
            FROM leads 
            WHERE telefono = '613523714' OR telefono2 = '613523714'
            LIMIT 5
        """)
        
        resultados = cursor.fetchall()
        
        print(f"Registros encontrados con teléfono 613523714: {len(resultados)}")
        for registro in resultados:
            print(f"  - {registro['nombre']} {registro['apellidos']}")
            print(f"    Teléfono: {registro['telefono']}")
            print(f"    Teléfono2: {registro['telefono2']}")
            print(f"    Origen: {registro['origen_archivo']}")
            print()
        
        # Verificar total de registros de Septiembre
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE origen_archivo = 'Septiembre'")
        total = cursor.fetchone()['total']
        print(f"Total registros de Septiembre en Railway: {total}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    verificar_telefono()
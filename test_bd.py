#!/usr/bin/env python3
"""
Test de conexión a la base de datos
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    print("Probando conexión a la base de datos...")
    
    # Configuración idéntica a api_resultado_llamada.py
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
    
    print(f"Configuración:")
    print(f"  Host: {DB_CONFIG['host']}")
    print(f"  Port: {DB_CONFIG['port']}")
    print(f"  User: {DB_CONFIG['user']}")
    print(f"  Database: {DB_CONFIG['database']}")
    
    try:
        print("\nIntentando conexión...")
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✅ Conexión exitosa!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        print(f"✅ Total de leads en BD: {count}")
        
        cursor.close()
        connection.close()
        print("✅ Conexión cerrada correctamente")
        
    except mysql.connector.Error as e:
        print(f"❌ Error de conexión: {e}")
        
        # Intentar fallback
        print("\nIntentando fallback sin SSL...")
        try:
            DB_CONFIG_FALLBACK = DB_CONFIG.copy()
            DB_CONFIG_FALLBACK.pop('ssl_disabled', None)
            connection = mysql.connector.connect(**DB_CONFIG_FALLBACK)
            print("✅ Conexión fallback exitosa!")
            connection.close()
        except mysql.connector.Error as e2:
            print(f"❌ Error en fallback: {e2}")

if __name__ == "__main__":
    test_connection()

#!/usr/bin/env python3
"""
Test de conexión a la base de datos de producción
"""

import mysql.connector
from config import settings

def test_production_connection():
    print("Probando conexión a la base de datos de PRODUCCIÓN...")
    
    # Configuración EXACTAMENTE igual a api_resultado_llamada.py
    DB_CONFIG = {
        'host': settings.DB_HOST,
        'port': settings.DB_PORT,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'database': settings.DB_DATABASE,
        'ssl_disabled': True,  # Deshabilitar SSL para evitar errores de conexión
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
        
        # Probar una consulta de búsqueda
        cursor.execute("SELECT telefono, status_level_1, status_level_2 FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 1", ("654902550",))
        result = cursor.fetchone()
        if result:
            print(f"✅ Test de búsqueda exitoso: {result}")
        else:
            print("⚠️ No se encontró el teléfono de prueba")
        
        cursor.close()
        connection.close()
        print("✅ Conexión cerrada correctamente")
        
    except mysql.connector.Error as err:
        print(f"❌ Error de conexión: {err}")
        
        # Intentar fallback como en api_resultado_llamada.py
        if 'SSL' in str(err) or '2026' in str(err):
            print("\nIntentando conexión sin SSL...")
            try:
                config_no_ssl = DB_CONFIG.copy()
                config_no_ssl['ssl_disabled'] = True
                connection = mysql.connector.connect(**config_no_ssl)
                print("✅ Conexión fallback exitosa!")
                connection.close()
            except mysql.connector.Error as err2:
                print(f"❌ Error en fallback: {err2}")

if __name__ == "__main__":
    test_production_connection()

#!/usr/bin/env python3
"""
Test de conexión a Railway MySQL
"""
import mysql.connector
from dotenv import load_dotenv
from config import settings

def test_railway_connection():
    """Probar conexión a Railway MySQL"""
    print("=== TEST DE CONEXIÓN A RAILWAY ===")
    print(f"DB_HOST: {settings.DB_HOST}")
    print(f"DB_PORT: {settings.DB_PORT}")
    print(f"DB_USER: {settings.DB_USER}")
    print(f"DB_DATABASE: {settings.DB_DATABASE}")
    print()
    
    try:
        # Probar conexión
        connection = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE
        )
        
        if connection.is_connected():
            print("✅ CONEXIÓN EXITOSA a Railway MySQL")
            
            cursor = connection.cursor()
            
            # Listar tablas
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"\n📋 Tablas encontradas ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
            
            # Si existe la tabla leads, contar registros
            if any('leads' in str(table) for table in tables):
                cursor.execute("SELECT COUNT(*) FROM leads")
                count = cursor.fetchone()[0]
                print(f"\n📊 Total registros en tabla leads: {count}")
                
                # Mostrar algunos ejemplos
                cursor.execute("SELECT telefono, status_level_1, status_level_2, updated_at FROM leads ORDER BY updated_at DESC LIMIT 3")
                results = cursor.fetchall()
                print("\n📝 Últimos 3 registros:")
                for result in results:
                    print(f"  {result[0]} | {result[1]} -> {result[2]} | {result[3]}")
            
            cursor.close()
            connection.close()
            
        else:
            print("❌ No se pudo establecer conexión")
            
    except mysql.connector.Error as err:
        print(f"❌ ERROR DE CONEXIÓN: {err}")
    except Exception as e:
        print(f"❌ ERROR GENERAL: {e}")

if __name__ == "__main__":
    test_railway_connection()
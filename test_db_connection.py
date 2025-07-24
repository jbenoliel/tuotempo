#!/usr/bin/env python3
"""
Script simple para testear la conexión a la base de datos local
y verificar que las tablas necesarias existen.
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_database_connection():
    """Prueba la conexión a la base de datos local"""
    print("=== TEST DE CONEXIÓN A BASE DE DATOS LOCAL ===")
    
    # Configuración de la base de datos
    db_config = {
        'host': os.getenv('MYSQLHOST', 'localhost'),
        'port': int(os.getenv('MYSQLPORT', 3306)),
        'user': os.getenv('MYSQLUSER', 'root'),
        'password': os.getenv('MYSQLPASSWORD'),
        'database': os.getenv('MYSQLDATABASE'),
        'ssl_disabled': True,
        'autocommit': True,
        'charset': 'utf8mb4',
        'use_unicode': True
    }
    
    print(f"Intentando conectar a: {db_config['host']}:{db_config['port']}")
    print(f"Base de datos: {db_config['database']}")
    print(f"Usuario: {db_config['user']}")
    
    try:
        # Intentar conexión
        connection = mysql.connector.connect(**db_config)
        print("✅ Conexión exitosa a MySQL")
        
        cursor = connection.cursor()
        
        # Verificar que la base de datos existe
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()[0]
        print(f"✅ Base de datos actual: {current_db}")
        
        # Listar tablas existentes
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"✅ Tablas encontradas ({len(tables)}):")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Verificar tabla leads
        if ('leads',) in tables:
            print("✅ Tabla 'leads' encontrada")
            
            # Verificar estructura de la tabla leads
            cursor.execute("DESCRIBE leads")
            columns = cursor.fetchall()
            
            # Buscar los nuevos campos de reservas automáticas
            column_names = [col[0] for col in columns]
            
            required_fields = ['reserva_automatica', 'preferencia_horario', 'fecha_minima_reserva']
            for field in required_fields:
                if field in column_names:
                    print(f"   ✅ Campo '{field}' existe")
                else:
                    print(f"   ❌ Campo '{field}' NO existe")
        else:
            print("❌ Tabla 'leads' NO encontrada")
        
        # Verificar tabla daemon_status
        if ('daemon_status',) in tables:
            print("✅ Tabla 'daemon_status' encontrada")
        else:
            print("❌ Tabla 'daemon_status' NO encontrada")
        
        # Verificar algunos datos de ejemplo
        cursor.execute("SELECT COUNT(*) FROM leads")
        lead_count = cursor.fetchone()[0]
        print(f"✅ Total de leads en la base de datos: {lead_count}")
        
        cursor.close()
        connection.close()
        print("✅ Conexión cerrada correctamente")
        
        return True
        
    except mysql.connector.Error as err:
        print(f"❌ Error de MySQL: {err}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_environment_variables():
    """Verifica que las variables de entorno estén configuradas"""
    print("\n=== TEST DE VARIABLES DE ENTORNO ===")
    
    required_vars = [
        'MYSQLHOST', 'MYSQLUSER', 'MYSQLPASSWORD', 
        'MYSQLDATABASE', 'MYSQLPORT'
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var:
                print(f"✅ {var}: ********")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NO CONFIGURADA")
            all_present = False
    
    # Variables adicionales para TuoTempo
    tuotempo_vars = [
        'TUOTEMPO_ENV', 'TUOTEMPO_API_KEY_PRE', 
        'TUOTEMPO_INSTANCE_ID', 'RESERVAS_DAEMON_ENABLED'
    ]
    
    print("\n--- Variables de TuoTempo ---")
    for var in tuotempo_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var:
                print(f"✅ {var}: ********")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: NO CONFIGURADA (opcional)")
    
    return all_present

if __name__ == "__main__":
    print("INICIANDO TESTS DE INFRAESTRUCTURA LOCAL")
    print("=" * 50)
    
    # Test 1: Variables de entorno
    env_ok = test_environment_variables()
    
    # Test 2: Conexión a base de datos
    db_ok = test_database_connection()
    
    print("\n" + "=" * 50)
    print("RESUMEN DE TESTS:")
    print(f"Variables de entorno: {'✅ OK' if env_ok else '❌ ERROR'}")
    print(f"Conexión a base de datos: {'✅ OK' if db_ok else '❌ ERROR'}")
    
    if env_ok and db_ok:
        print("\n🎉 TODOS LOS TESTS PASARON - Listo para iniciar la aplicación")
        exit(0)
    else:
        print("\n💥 ALGUNOS TESTS FALLARON - Revisar configuración")
        exit(1)

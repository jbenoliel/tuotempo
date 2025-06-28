import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_railway_database():
    """Crear la base de datos Segurcaixa en Railway"""
    try:
        # Configuración sin especificar la base de datos
        config = {
            'host': os.environ.get('MYSQLHOST') or 'mysql.railway.internal',
            'user': os.environ.get('MYSQLUSER') or 'root',
            'password': os.environ.get('MYSQLPASSWORD') or '',
            'port': int(os.environ.get('MYSQLPORT') or 3306)
        }
        
        print(f"Intentando conectar a MySQL con: {config['host']}:{config['port']} como {config['user']}")
        
        # Conectar sin especificar base de datos
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Crear la base de datos
        print("Creando base de datos 'Segurcaixa'...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS Segurcaixa")
        print("Base de datos creada correctamente")
        
        # Verificar que se creó
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor]
        print(f"Bases de datos disponibles: {databases}")
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        
        return True
    except Exception as e:
        print(f"Error al crear la base de datos: {e}")
        return False

if __name__ == "__main__":
    create_railway_database()

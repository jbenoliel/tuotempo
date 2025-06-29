import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_leads_table():
    """Crear la tabla leads en la base de datos Railway"""
    try:
        # Configuración para Railway
        config = {
            'host': 'mysql.railway.internal',
            'user': 'root',
            'password': os.environ.get('MYSQLPASSWORD', ''),
            'database': 'railway',
            'auth_plugin': 'mysql_native_password'
        }
        
        print(f"Intentando conectar a MySQL con configuración:")
        print(f"Config: {config}")
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(**config)
        print("¡Conexión exitosa a MySQL!")
        cursor = connection.cursor()
        
        # Crear tabla leads
        create_table_query = (
            "CREATE TABLE IF NOT EXISTS leads ("
            "id INT AUTO_INCREMENT PRIMARY KEY,"
            "nombre VARCHAR(100),"
            "apellidos VARCHAR(150),"
            "nombre_clinica VARCHAR(255),"
            "direccion_clinica VARCHAR(255),"
            "codigo_postal VARCHAR(10),"
            "ciudad VARCHAR(100),"
            "telefono VARCHAR(20),"
            "area_id VARCHAR(100),"
            "match_source VARCHAR(50),"
            "match_confidence INT,"
            "cita DATETIME NULL,"
            "conPack BOOLEAN DEFAULT FALSE,"
            "ultimo_estado ENUM('no answer', 'busy', 'completed') NULL"
            ")"
        )
        
        cursor.execute(create_table_query)
        print("Tabla 'leads' creada correctamente en Railway")
        
        # Verificar que se creó
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        print(f"Tablas disponibles: {tables}")
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    create_leads_table()

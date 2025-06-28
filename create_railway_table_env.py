import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_leads_table():
    """Crear la tabla leads en la base de datos Railway"""
    try:
        # Obtener variables de entorno de Railway
        host = os.environ.get('MYSQLHOST') or os.environ.get('DATABASE_URL', 'localhost')
        user = os.environ.get('MYSQLUSER', 'root')
        password = os.environ.get('MYSQLPASSWORD', '')
        database = os.environ.get('MYSQLDATABASE', 'railway')
        port = int(os.environ.get('MYSQLPORT', 3306))
        
        # Configuración para Railway
        config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'port': port
        }
        
        # Mostrar configuración (ocultando contraseña)
        safe_config = config.copy()
        if 'password' in safe_config and safe_config['password']:
            safe_config['password'] = safe_config['password'][:3] + '****' if len(safe_config['password']) > 3 else '****'
        print(f"Intentando conectar a MySQL con configuración:")
        print(f"Config: {safe_config}")
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(**config)
        print("¡Conexión exitosa a MySQL!")
        cursor = connection.cursor()
        
        # Verificar si la tabla ya existe
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            print(f"La tabla 'leads' ya existe. Total registros: {count}")
        except mysql.connector.Error as err:
            if err.errno == 1146:  # Table doesn't exist
                print("La tabla 'leads' no existe. Creándola...")
                # Crear tabla leads
                create_table_query = (
                    "CREATE TABLE leads ("
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
                print("Tabla 'leads' creada correctamente")
            else:
                raise
        
        # Verificar tablas disponibles
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        print(f"Tablas disponibles en la base de datos: {tables}")
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        print("Conexión cerrada")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando creación de tabla leads en Railway...")
    result = create_leads_table()
    print(f"Proceso completado: {'Éxito' if result else 'Falló'}")

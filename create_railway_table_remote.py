import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def create_leads_table():
    """Crear la tabla leads en la base de datos Railway (conexión remota)"""
    try:
        # Configuración para Railway (conexión remota)
        # Necesitas obtener estos valores de tu dashboard de Railway
        config = {
            'host': os.environ.get('RAILWAY_DB_HOST', ''),  # Ej: containers-us-west-XXX.railway.app
            'user': os.environ.get('RAILWAY_DB_USER', 'root'),
            'password': os.environ.get('RAILWAY_DB_PASSWORD', ''),
            'database': os.environ.get('RAILWAY_DB_NAME', 'railway'),
            'port': int(os.environ.get('RAILWAY_DB_PORT', '3306'))
        }
        
        # Mostrar configuración (ocultando contraseña)
        safe_config = config.copy()
        if 'password' in safe_config and safe_config['password']:
            safe_config['password'] = safe_config['password'][:3] + '****' if len(safe_config['password']) > 3 else '****'
        print(f"Intentando conectar a MySQL Railway (remoto) con configuración:")
        print(f"Config: {safe_config}")
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(**config)
        print("¡Conexión exitosa a MySQL Railway!")
        cursor = connection.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("SHOW TABLES LIKE 'leads'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("La tabla 'leads' ya existe en la base de datos")
        else:
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
            print("Tabla 'leads' creada correctamente en Railway")
        
        # Verificar tablas disponibles
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        print(f"Tablas disponibles en la base de datos: {tables}")
        
        # Obtener estadísticas
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            print(f"Total registros en leads: {count}")
        except Exception as e:
            print(f"Error al obtener estadísticas: {e}")
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        print("Conexión cerrada")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando creación de tabla leads en Railway (conexión remota)...")
    result = create_leads_table()
    print(f"Proceso completado: {'Éxito' if result else 'Falló'}")

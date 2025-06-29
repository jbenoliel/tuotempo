import mysql.connector
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Inicializa la base de datos y crea las tablas necesarias si no existen"""
    try:
        # Configuración para la base de datos
        config = {
            'host': os.environ.get('MYSQLHOST', 'localhost'),
            'user': os.environ.get('MYSQLUSER', 'root'),
            'password': os.environ.get('MYSQLPASSWORD', ''),
            'database': os.environ.get('MYSQLDATABASE', 'railway'),
            'port': int(os.environ.get('MYSQLPORT', 3306))
        }
        
        # Mostrar configuración (ocultando contraseña)
        safe_config = config.copy()
        if 'password' in safe_config and safe_config['password']:
            safe_config['password'] = safe_config['password'][:3] + '****' if len(safe_config['password']) > 3 else '****'
        logger.info(f"Intentando conectar a MySQL con configuración: {safe_config}")
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(**config)
        logger.info("¡Conexión exitosa a MySQL!")
        cursor = connection.cursor()
        
        # Verificar si la tabla leads ya existe
        try:
            cursor.execute("SELECT COUNT(*) FROM leads")
            count = cursor.fetchone()[0]
            logger.info(f"La tabla 'leads' ya existe. Total registros: {count}")
        except mysql.connector.Error as err:
            if err.errno == 1146:  # Table doesn't exist
                logger.info("La tabla 'leads' no existe. Creándola...")
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
                logger.info("Tabla 'leads' creada correctamente")
            else:
                logger.error(f"Error al verificar tabla leads: {err}")
                raise
        
        # Verificar tablas disponibles
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        logger.info(f"Tablas disponibles en la base de datos: {tables}")
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        logger.info("Conexión cerrada")
        
        return True
    except Exception as e:
        logger.error(f"Error en init_database: {e}")
        return False

if __name__ == "__main__":
    init_database()

import os
import mysql.connector
import pandas as pd
import logging
from urllib.request import urlopen
from io import BytesIO
import sys

# Configurar logging
log_file = 'railway_import.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Obtener conexión a la base de datos en el entorno de Railway"""
    try:
        # En Railway, el host es mysql.railway.internal
        config = {
            'host': 'mysql.railway.internal',
            'user': 'root',
            'password': os.environ.get('MYSQLPASSWORD', ''),
            'database': 'railway',
            'port': int(os.environ.get('MYSQLPORT', 3306))
        }
        
        logger.info(f"Conectando a MySQL en {config['host']}:{config['port']} como {config['user']}")
        connection = mysql.connector.connect(**config)
        logger.info("Conexión exitosa a la base de datos")
        return connection
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None

def create_leads_table(connection):
    """Crear la tabla leads si no existe"""
    try:
        cursor = connection.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("SHOW TABLES LIKE 'leads'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            logger.info("La tabla 'leads' no existe. Creándola...")
            
            # Crear la tabla leads
            create_table_query = """
            CREATE TABLE leads (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255),
                apellidos VARCHAR(255),
                nombre_clinica VARCHAR(255),
                direccion_clinica TEXT,
                codigo_postal VARCHAR(10),
                ciudad VARCHAR(255),
                telefono VARCHAR(20),
                area_id VARCHAR(50),
                match_source VARCHAR(100),
                match_confidence FLOAT,
                cita DATETIME,
                conPack BOOLEAN,
                ultimo_estado VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
            logger.info("Tabla 'leads' creada exitosamente")
        else:
            logger.info("La tabla 'leads' ya existe")
        
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Error al crear la tabla: {e}")
        return False

def load_data_from_url(connection, url):
    """Cargar datos desde una URL de Excel"""
    try:
        logger.info(f"Descargando Excel desde URL: {url}")
        response = urlopen(url)
        excel_data = response.read()
        
        # Leer el Excel desde los bytes descargados
        df = pd.read_excel(BytesIO(excel_data))
        logger.info(f"Excel leído exitosamente. {len(df)} filas encontradas.")
        
        # Truncar la tabla para evitar duplicados
        cursor = connection.cursor()
        logger.info("Truncando tabla leads...")
        cursor.execute("TRUNCATE TABLE leads")
        
        # Preparar los datos para inserción
        records = []
        for _, row in df.iterrows():
            record = (
                str(row.get('NOMBRE', '')),
                str(row.get('APELLIDOS', '')),
                str(row.get('NOMBRE_CLINICA', '')),
                str(row.get('DIRECCION_CLINICA', '')),
                '',  # código postal
                '',  # ciudad
                str(row.get('TELEFONO', '')),
                str(row.get('areaId', '')),
                '',  # match_source
                0,   # match_confidence
                None,  # cita
                False,  # conPack
                None   # ultimo_estado
            )
            records.append(record)
        
        # Insertar los datos
        insert_query = """
        INSERT INTO leads (
            nombre, apellidos, nombre_clinica, direccion_clinica, codigo_postal, ciudad, telefono, 
            area_id, match_source, match_confidence, cita, conPack, ultimo_estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        logger.info(f"Insertando {len(records)} registros en la tabla leads...")
        cursor.executemany(insert_query, records)
        connection.commit()
        
        logger.info(f"Se insertaron {cursor.rowcount} registros en la tabla 'leads'")
        
        # Verificar que se insertaron los datos
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        logger.info(f"Total registros en leads después de la inserción: {count}")
        
        cursor.close()
        return True
    except Exception as e:
        logger.error(f"Error al cargar datos: {e}")
        return False

def main():
    # Verificar que estamos en Railway
    if 'RAILWAY_ENVIRONMENT' not in os.environ:
        logger.error("Este script debe ejecutarse en el entorno de Railway usando 'railway run'")
        logger.error("Ejecuta: railway run python railway_import_data.py URL_DEL_EXCEL")
        return False
    
    # Obtener URL del Excel como argumento
    if len(sys.argv) < 2:
        logger.error("Debes proporcionar la URL del archivo Excel como argumento")
        logger.error("Ejemplo: railway run python railway_import_data.py https://ejemplo.com/datos.xlsx")
        return False
    
    excel_url = sys.argv[1]
    
    # Conectar a la base de datos
    connection = get_db_connection()
    if not connection:
        return False
    
    # Crear la tabla si no existe
    if not create_leads_table(connection):
        connection.close()
        return False
    
    # Cargar datos desde la URL
    success = load_data_from_url(connection, excel_url)
    
    # Cerrar conexión
    connection.close()
    logger.info("Conexión cerrada")
    
    return success

if __name__ == "__main__":
    logger.info("Iniciando importación de datos a Railway...")
    if main():
        logger.info("Importación completada exitosamente")
    else:
        logger.error("Error en la importación de datos")
        sys.exit(1)

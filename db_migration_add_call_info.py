import os
import pymysql
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos."""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            cursorclass=pymysql.cursors.DictCursor
        )
        logging.info("Conexión a la base de datos establecida con éxito.")
        return connection
    except pymysql.MySQLError as e:
        logging.error(f"Error al conectar con la base de datos: {e}")
        raise

def add_column_if_not_exists(cursor, table_name, column_name, column_definition):
    """Añade una columna a una tabla si no existe."""
    try:
        cursor.execute(f"SELECT `{column_name}` FROM `{table_name}` LIMIT 1;")
        logging.info(f"La columna '{column_name}' ya existe en la tabla '{table_name}'. No se realizarán cambios.")
    except pymysql.err.OperationalError as e:
        # El error 1054 indica que la columna no existe, lo cual es esperado
        if e.args[0] == 1054:
            try:
                alter_query = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_definition};"
                cursor.execute(alter_query)
                logging.info(f"Columna '{column_name}' añadida con éxito a la tabla '{table_name}'.")
            except pymysql.MySQLError as alter_e:
                logging.error(f"Error al añadir la columna '{column_name}': {alter_e}")
                raise
        else:
            # Si es otro error, lo relanzamos
            raise

def main():
    """Función principal para ejecutar la migración de la base de datos."""
    logging.info("Iniciando migración de la base de datos para añadir información de llamadas.")
    
    connection = None
    try:
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            table_name = 'leads'
            
            # Definición de las nuevas columnas
            columns_to_add = {
                'call_id': 'VARCHAR(255) NULL',
                'call_time': 'DATETIME NULL',
                'call_duration': 'INT NULL',
                'call_summary': 'TEXT NULL',
                'call_recording_url': 'VARCHAR(512) NULL',
                'status_level_1': 'VARCHAR(100) NULL',
                'status_level_2': 'VARCHAR(100) NULL'
            }
            
            for col_name, col_def in columns_to_add.items():
                add_column_if_not_exists(cursor, table_name, col_name, col_def)

        connection.commit()
        logging.info("Migración de la base de datos completada con éxito.")
        
    except Exception as e:
        logging.error(f"Ha ocurrido un error durante la migración: {e}")
        if connection:
            connection.rollback()
            logging.info("Se ha hecho rollback de la transacción.")
    finally:
        if connection:
            connection.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    main()

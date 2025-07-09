import os
import pymysql
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse

"""Script de migración para crear la tabla `pearl_calls` y enlazarla con `leads`.

La tabla almacena la información de las llamadas extraídas de Pearl (call center / NLPearl).
Ejecútalo una sola vez (o inclúyelo en tu pipeline de CI/CD) para garantizar que la
base de datos contiene la estructura necesaria antes de lanzar el scheduler.
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

def get_db_connection():
    """Devuelve conexión a MySQL usando MYSQL_URL o variables independientes."""
    mysql_url = os.getenv("MYSQL_URL")
    try:
        if mysql_url:
            logging.info("Usando MYSQL_URL para la conexión.")
            url = urlparse(mysql_url)
            params = {
                "host": url.hostname,
                "user": url.username,
                "password": url.password,
                "database": url.path[1:],
                "cursorclass": pymysql.cursors.DictCursor,
            }
            if url.port:
                params["port"] = url.port
        else:
            logging.info("Usando variables MYSQL_* para la conexión.")
            params = {
                "host": os.getenv("MYSQL_HOST"),
                "user": os.getenv("MYSQL_USER"),
                "password": os.getenv("MYSQL_PASSWORD"),
                "database": os.getenv("MYSQL_DATABASE"),
                "port": int(os.getenv("MYSQL_PORT", 3306)),
                "cursorclass": pymysql.cursors.DictCursor,
            }
        return pymysql.connect(**params)
    except Exception as e:
        logging.error(f"Error conectando a MySQL: {e}")
        raise

def table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None

def create_table(cursor):
    logging.info("Creando tabla 'pearl_calls' si no existe…")
    create_sql = """
    CREATE TABLE `pearl_calls` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `call_id` VARCHAR(64) NOT NULL UNIQUE,
        `phone_number` VARCHAR(20) NOT NULL,
        `call_time` DATETIME NOT NULL,
        `duration` INT DEFAULT 0,
        `summary` TEXT,
        `collected_info` JSON,
        `recording_url` VARCHAR(512),
        `lead_id` INT NULL,
        INDEX `idx_phone` (`phone_number`),
        CONSTRAINT `fk_pearl_calls_lead` FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    cursor.execute(create_sql)


def main():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if table_exists(cursor, "pearl_calls"):
                logging.info("La tabla 'pearl_calls' ya existe. No se realizan cambios.")
            else:
                create_table(cursor)
                logging.info("Tabla 'pearl_calls' creada correctamente.")
        conn.commit()
    except Exception as err:
        logging.error(f"Fallo en la migración: {err}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logging.info("Conexión cerrada.")

if __name__ == "__main__":
    main()

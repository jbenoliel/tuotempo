import os
import pymysql
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse

"""Script de migración para actualizar la tabla `usuarios` con campos para autenticación por email.

Este script añade campos necesarios para el sistema de autenticación con restablecimiento
de contraseña por email: email, reset_token, reset_token_expiry, is_active, y email_verified.
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
        else:
            logging.info("Usando variables de entorno individuales para la conexión.")
            params = {
                "host": os.getenv("MYSQL_HOST", "localhost"),
                "user": os.getenv("MYSQL_USER", "root"),
                "password": os.getenv("MYSQL_PASSWORD", ""),
                "database": os.getenv("MYSQL_DATABASE", "tuotempo"),
                "cursorclass": pymysql.cursors.DictCursor,
            }
        
        connection = pymysql.connect(**params)
        logging.info("Conexión a la base de datos establecida con éxito.")
        return connection
    except Exception as e:
        logging.error(f"Error al conectar a la base de datos: {e}")
        raise

def table_exists(cursor, table_name: str) -> bool:
    """Verifica si una tabla existe en la base de datos."""
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None

def column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Verifica si una columna existe en una tabla."""
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None

def update_usuarios_table(cursor):
    """Actualiza la tabla usuarios con los campos necesarios para autenticación por email."""
    if not table_exists(cursor, "usuarios"):
        logging.info("La tabla 'usuarios' no existe. Creándola...")
        cursor.execute("""
        CREATE TABLE usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            is_admin BOOLEAN DEFAULT FALSE,
            reset_token VARCHAR(255) NULL,
            reset_token_expiry DATETIME NULL,
            is_active BOOLEAN DEFAULT TRUE,
            email_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        logging.info("Tabla 'usuarios' creada exitosamente.")
    else:
        logging.info("La tabla 'usuarios' ya existe. Verificando y añadiendo columnas faltantes...")
        
        # Verificar y añadir columna email si no existe
        if not column_exists(cursor, "usuarios", "email"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) NULL UNIQUE")
            logging.info("Columna 'email' añadida a la tabla 'usuarios'.")
        
        # Verificar y añadir columna reset_token si no existe
        if not column_exists(cursor, "usuarios", "reset_token"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN reset_token VARCHAR(255) NULL")
            logging.info("Columna 'reset_token' añadida a la tabla 'usuarios'.")
        
        # Verificar y añadir columna reset_token_expiry si no existe
        if not column_exists(cursor, "usuarios", "reset_token_expiry"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN reset_token_expiry DATETIME NULL")
            logging.info("Columna 'reset_token_expiry' añadida a la tabla 'usuarios'.")
        
        # Verificar y añadir columna is_active si no existe
        if not column_exists(cursor, "usuarios", "is_active"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            logging.info("Columna 'is_active' añadida a la tabla 'usuarios'.")
        
        # Verificar y añadir columna email_verified si no existe
        if not column_exists(cursor, "usuarios", "email_verified"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
            logging.info("Columna 'email_verified' añadida a la tabla 'usuarios'.")
        
        # Verificar y añadir columnas de timestamps si no existen
        if not column_exists(cursor, "usuarios", "created_at"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            logging.info("Columna 'created_at' añadida a la tabla 'usuarios'.")
        
        if not column_exists(cursor, "usuarios", "updated_at"):
            cursor.execute("ALTER TABLE usuarios ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            logging.info("Columna 'updated_at' añadida a la tabla 'usuarios'.")

def main():
    """Función principal que ejecuta la migración."""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            update_usuarios_table(cursor)
        
        connection.commit()
        logging.info("Migración completada con éxito.")
    except Exception as e:
        logging.error(f"Error durante la migración: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    main()

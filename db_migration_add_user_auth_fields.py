"""
Script de migración para añadir campos de autenticación y estado a la tabla de usuarios.

Añade las siguientes columnas a la tabla `usuarios` si no existen:
- email: VARCHAR(255) UNIQUE
- is_admin: BOOLEAN (TINYINT(1)) con valor por defecto 0 (False)
- is_active: BOOLEAN (TINYINT(1)) con valor por defecto 1 (True)
- email_verified: BOOLEAN (TINYINT(1)) con valor por defecto 0 (False)

Este script es idempotente y puede ejecutarse de forma segura varias veces.
"""
import logging
from db import get_connection, get_database_name

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')
logger = logging.getLogger(__name__)

def column_exists(cursor, table_name, column_name):
    """Verifica si una columna ya existe en una tabla."""
    db_name = get_database_name()
    if not db_name:
        logger.error("No se pudo obtener el nombre de la base de datos desde las variables de entorno.")
        return False
        
    query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND COLUMN_NAME = %s
    """
    cursor.execute(query, (db_name, table_name, column_name))
    return cursor.fetchone()[0] > 0

def add_column_if_not_exists(cursor, table_name, column_definition):
    """Añade una columna a una tabla si no existe, extrayendo el nombre de la definición."""
    # Extraer el nombre de la columna de la definición (la primera palabra)
    column_name = column_definition.strip().split()[0].strip('`')
    
    if not column_exists(cursor, table_name, column_name):
        logger.info(f"La columna '{column_name}' no existe en la tabla '{table_name}'. Creándola...")
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
            logger.info(f"✅ Columna '{column_name}' creada exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error al crear la columna '{column_name}': {e}")
    else:
        logger.info(f"La columna '{column_name}' ya existe en la tabla '{table_name}'. No se requieren cambios.")

def run_migration():
    """Ejecuta la migración para añadir las columnas a la tabla de usuarios."""
    logger.info("--- Iniciando migración para la tabla 'usuarios' ---")
    db_conn = None
    try:
        db_conn = get_connection()
        if not db_conn:
            logger.error("No se pudo establecer conexión con la base de datos para la migración.")
            return

        cursor = db_conn.cursor()
        table_name = 'usuarios'

        # Definiciones de las columnas a añadir
        columns_to_add = [
            '`email` VARCHAR(255) UNIQUE NULL AFTER `password_hash`',
            '`is_admin` TINYINT(1) NOT NULL DEFAULT 0 AFTER `email`',
            '`is_active` TINYINT(1) NOT NULL DEFAULT 1 AFTER `is_admin`',
            '`email_verified` TINYINT(1) NOT NULL DEFAULT 0 AFTER `is_active`'
        ]

        for col_def in columns_to_add:
            add_column_if_not_exists(cursor, table_name, col_def)

        db_conn.commit()
        logger.info("--- Migración para la tabla 'usuarios' completada exitosamente ---")

    except Exception as e:
        logger.error(f"Error catastrófico durante la migración de 'usuarios': {e}")
        if db_conn:
            db_conn.rollback()
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            logger.info("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    run_migration()

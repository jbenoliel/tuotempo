"""
Sistema de Migración Inteligente basado en Esquemas.

Compara el esquema de la base de datos activa con la definición en `schema.sql`
y aplica las diferencias (nuevas tablas, nuevas columnas) de forma automática.
"""

import logging
import re
import sys
from db import get_connection, get_database_name

# Configurar logging para que sea visible en los logs de Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(process)d] - [%(funcName)s] - %(message)s',
    stream=sys.stdout # Forzar salida a stdout
)
logger = logging.getLogger(__name__)

def parse_sql_schema(file_path='schema.sql'):
    """Analiza un fichero .sql y extrae la definición de las tablas y columnas."""
    ideal_schema = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"El fichero de esquema '{file_path}' no fue encontrado.")
        return {}

    # Eliminar sentencias INSERT para procesar solo la estructura
    content = re.sub(r'INSERT INTO .*?;', '', content, flags=re.IGNORECASE | re.DOTALL)


    table_definitions = re.findall(r'(CREATE TABLE `?\w+`? .*?\);)', content, re.DOTALL | re.IGNORECASE)
    
    for full_create_statement in table_definitions:
        table_name_match = re.search(r'CREATE TABLE `?(\w+)`?', full_create_statement, re.IGNORECASE)
        if not table_name_match:
            continue
        table_name = table_name_match.group(1)

        ideal_schema[table_name] = {'full_statement': full_create_statement, 'columns': {}}

        columns_str_match = re.search(r'\((.*)\)', full_create_statement, re.DOTALL)
        if not columns_str_match:
            continue
        columns_str = columns_str_match.group(1)

        column_lines = [line.strip() for line in columns_str.strip().split('\n') if line.strip()]
        
        for line in column_lines:
            line_lower = line.lower()
            # Ignorar líneas que no son definiciones de columna (claves, índices, etc.)
            if line_lower.startswith(('primary key', 'constraint', 'foreign key', 'index', 'key', ')', 'engine=', 'create index')):
                continue

            col_name_match = re.match(r'`?(\w+)`?', line)
            if col_name_match:
                col_name = col_name_match.group(1)
                ideal_schema[table_name]['columns'][col_name] = line.rstrip(',')

    logger.info(f"Esquema ideal cargado desde '{file_path}' con {len(ideal_schema)} tablas.")
    return ideal_schema

def get_current_schema(cursor):
    """Inspecciona la base de datos y devuelve su esquema actual."""
    db_name = get_database_name()
    if not db_name:
        logger.error("No se pudo obtener el nombre de la base de datos.")
        return {}

    schema = {}
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]

    for table_name in tables:
        schema[table_name] = {}
        query = """
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        cursor.execute(query, (db_name, table_name))
        schema[table_name] = {row[0] for row in cursor.fetchall()}

    logger.info(f"Esquema actual de la base de datos '{db_name}' cargado con {len(schema)} tablas.")
    return schema

def compare_and_apply_schema(db_conn, ideal_schema, current_schema):
    """Compara y aplica cambios. Devuelve True si todo fue exitoso, False si hubo algún error."""
    logger.info("--- Comparando esquemas y aplicando migraciones ---")
    all_ok = True
    cursor = db_conn.cursor()

    # Paso 1: Crear tablas faltantes
    for table_name, table_data in ideal_schema.items():
        if table_name not in current_schema:
            logger.info(f"La tabla '{table_name}' no existe. Creándola...")
            try:
                cursor.execute(table_data['full_statement'])
                logger.info(f"✅ Tabla '{table_name}' creada exitosamente.")
            except Exception as e:
                logger.error(f"❌ Error al crear la tabla '{table_name}': {e}", exc_info=True)
                all_ok = False
    
    if not all_ok:
        logger.error("Errores al crear tablas. Abortando migración de columnas.")
        return False

    logger.info("Recargando esquema actual después de la creación de tablas...")
    current_schema = get_current_schema(db_conn.cursor())

    # Paso 2: Añadir columnas faltantes
    for table_name, table_data in ideal_schema.items():
        if table_name not in current_schema:
            continue
        for col_name, col_definition in table_data['columns'].items():
            if col_name not in current_schema[table_name]:
                logger.info(f"Columna '{col_name}' no existe en '{table_name}'. Añadiéndola...")
                try:
                    query = f"ALTER TABLE `{table_name}` ADD COLUMN {col_definition}"
                    cursor.execute(query)
                    logger.info(f"✅ Columna '{col_name}' añadida a '{table_name}'.")
                except Exception as e:
                    logger.error(f"❌ Error al añadir columna '{col_name}' a '{table_name}': {e}", exc_info=True)
                    all_ok = False
    return all_ok

def run_intelligent_migration():
    """Punto de entrada para la migración inteligente. Devuelve True en éxito, False en fallo."""
    logger.info("--- Iniciando Migración Inteligente de Base de Datos ---")
    db_conn = None
    try:
        db_conn = get_connection()
        if not db_conn:
            logger.error("No se pudo establecer conexión con la base de datos.")
            return False

        ideal_schema = parse_sql_schema()
        if not ideal_schema:
            logger.error("No se pudo parsear el esquema ideal. Abortando.")
            return False

        current_schema = get_current_schema(db_conn.cursor())

        success = compare_and_apply_schema(db_conn, ideal_schema, current_schema)

        if success:
            db_conn.commit()
            logger.info("Cambios de migración confirmados en la base de datos.")
            return True
        else:
            logger.error("Se detectaron errores durante la migración. Revirtiendo cambios...")
            db_conn.rollback()
            return False

    except Exception as e:
        logger.error(f"Error catastrófico durante la migración inteligente: {e}", exc_info=True)
        if db_conn:
            db_conn.rollback()
        return False
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            logger.info("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    run_intelligent_migration()

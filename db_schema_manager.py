"""
Sistema de Migración Inteligente basado en Esquemas.

Compara el esquema de la base de datos activa con la definición en `schema.sql`
y aplica las diferencias (nuevas tablas, nuevas columnas) de forma automática.
"""

import re
import os
import sys
import logging
from db import get_connection, get_database_name

# Usar el logger existente sin reconfigurar
logger = logging.getLogger(__name__)

def parse_sql_schema():
    """Parsea un fichero .sql de forma robusta, sentencia por sentencia, con logging detallado."""
    try:
        # Usar una ruta absoluta garantiza que se encuentre el fichero sin importar desde dónde se ejecute el script.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, 'schema.sql')
        logger.info(f"[MIGRATION-PARSE] Buscando schema.sql en la ruta absoluta: {file_path}")

        if not os.path.exists(file_path):
            logger.critical(f"[MIGRATION-PARSE-CRITICAL] ¡ERROR FATAL! El fichero 'schema.sql' no existe en la ruta esperada. La migración no puede continuar.")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                logger.critical(f"[MIGRATION-PARSE-CRITICAL] ¡ERROR FATAL! El fichero 'schema.sql' está completamente vacío. La migración no puede continuar.")
                return None
        
        logger.info("[MIGRATION-PARSE] Fichero 'schema.sql' encontrado y con contenido.")

        # Dividir el script por ';' para obtener sentencias individuales. Filtrar cadenas vacías.
        sql_statements = [s.strip() for s in content.split(';') if s.strip()]
        logger.info(f"[MIGRATION-PARSE] Encontradas {len(sql_statements)} sentencias SQL candidatas en 'schema.sql'.")

        schema = {}
        create_table_count = 0
        for i, statement in enumerate(sql_statements):
            # Solo nos interesan las sentencias que definen la estructura de una tabla.
            if not statement.upper().startswith('CREATE TABLE'):
                logger.debug(f"[MIGRATION-PARSE] Ignorando sentencia #{i+1} (no es CREATE TABLE): {statement[:60]}...")
                continue
            
            create_table_count += 1
            # Extraer el nombre de la tabla de forma segura, con o sin backticks.
            table_name_match = re.search(r'CREATE TABLE\s+`?(\w+)`?', statement, re.IGNORECASE)
            if not table_name_match:
                logger.warning(f"[MIGRATION-PARSE-WARN] Se encontró una sentencia 'CREATE TABLE' pero no se pudo extraer el nombre de la tabla: {statement[:100]}...")
                continue
            
            table_name = table_name_match.group(1)
            logger.debug(f"[MIGRATION-PARSE] Procesando tabla '{table_name}'...")
            schema[table_name] = {'columns': {}, 'full_statement': statement + ';'}

            # Extraer el bloque de definiciones entre los paréntesis principales.
            columns_block_match = re.search(r'\((.*)\)', statement, re.DOTALL)
            if not columns_block_match:
                logger.warning(f"[MIGRATION-PARSE-WARN] No se pudo extraer el bloque de columnas para la tabla '{table_name}'.")
                continue
            
            columns_block = columns_block_match.group(1)
            # Dividir por saltos de línea y limpiar para obtener cada línea de definición.
            column_lines = [line.strip() for line in columns_block.split('\n') if line.strip()]

            for line in column_lines:
                clean_line = line.upper().strip()
                # Ignorar líneas que no son definiciones de columnas (claves, índices, etc.).
                if clean_line.startswith(('PRIMARY KEY', 'CONSTRAINT', 'FOREIGN KEY', 'INDEX', 'KEY', ')')):
                    continue
                
                # Extraer el nombre de la columna.
                col_name_match = re.match(r'`?(\w+)`?', line)
                if col_name_match:
                    col_name = col_name_match.group(1)
                    # Guardar la definición completa de la columna, quitando la coma final si existe.
                    schema[table_name]['columns'][col_name] = line.rstrip(',')
                    logger.debug(f"[MIGRATION-PARSE]    -> Columna encontrada: '{col_name}' en tabla '{table_name}'.")

        logger.info(f"[MIGRATION-PARSE] Análisis finalizado. Se procesaron {create_table_count} sentencias 'CREATE TABLE'.")
        logger.info(f"[MIGRATION-PARSE] Esquema ideal cargado con {len(schema)} tablas. Listo para comparar.")
        return schema

    except Exception as e:
        logger.critical(f"[MIGRATION-PARSE-CRITICAL] Ocurrió un error fatal e inesperado durante el parseo de 'schema.sql': {e}", exc_info=True)
        return None

def get_current_schema(cursor):
    """Inspecciona la base de datos y devuelve su esquema actual."""
    try:
        db_name = get_database_name()
        logger.info(f"--- Inspeccionando esquema actual de la base de datos '{db_name}' ---")
        current_schema = {}
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        logger.info(f"Se encontraron {len(tables)} tablas en la base de datos.")

        for table_name in tables:
            current_schema[table_name] = {'columns': {}}
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col[0]
                current_schema[table_name]['columns'][col_name] = col[1] # col[1] es el tipo de dato
        
        logger.info(f"Inspección del esquema actual finalizada.")
        return current_schema
    except Exception as e:
        logger.error(f"[MIGRATION-DB-ERROR] Error al inspeccionar el esquema de la DB: {e}", exc_info=True)
        return None

def compare_and_apply_schema(db_conn, ideal_schema, current_schema):
    """Compara el esquema ideal con el actual y aplica los cambios necesarios."""
    logger.info("--- Comparando esquemas y aplicando migraciones ---")
    all_ok = True
    cursor = db_conn.cursor()

    # 1. Crear tablas que no existen en la base de datos.
    for table_name, table_data in ideal_schema.items():
        if table_name not in current_schema:
            try:
                full_statement = table_data['full_statement']
                logger.info(f"[MIGRATION-APPLY] La tabla '{table_name}' no existe. Creándola ahora...")
                logger.debug(f"[MIGRATION-APPLY-SQL] EJECUTANDO: {full_statement}")
                cursor.execute(full_statement)
                logger.info(f"[MIGRATION-APPLY] ✅ Tabla '{table_name}' creada exitosamente.")
            except Exception as e:
                logger.error(f"[MIGRATION-APPLY-ERROR] ❌ Error al crear la tabla '{table_name}': {e}", exc_info=True)
                all_ok = False

    # Es crucial volver a obtener el esquema actual por si se crearon tablas nuevas.
    logger.info("[MIGRATION-APPLY] Re-inspeccionando esquema de la DB después de crear tablas...")
    current_schema = get_current_schema(cursor)
    if current_schema is None:
        logger.error("[MIGRATION-APPLY-ERROR] No se pudo re-inspeccionar el esquema. Abortando fase de columnas.")
        return False # No se puede continuar si no sabemos el estado actual

    # 2. Añadir columnas que no existen en tablas existentes.
    for table_name, table_data in ideal_schema.items():
        if table_name in current_schema:
            for col_name, col_def in table_data['columns'].items():
                if col_name not in current_schema[table_name]['columns']:
                    try:
                        query = f"ALTER TABLE `{table_name}` ADD COLUMN {col_def}"
                        logger.info(f"[MIGRATION-APPLY] La columna '{col_name}' no existe en '{table_name}'. Añadiéndola...")
                        logger.debug(f"[MIGRATION-APPLY-SQL] EJECUTANDO: {query}")
                        cursor.execute(query)
                        logger.info(f"[MIGRATION-APPLY] ✅ Columna '{col_name}' añadida a '{table_name}' exitosamente.")
                    except Exception as e:
                        logger.error(f"[MIGRATION-APPLY-ERROR] ❌ Error al añadir columna '{col_name}' a '{table_name}': {e}", exc_info=True)
                        all_ok = False
    
    cursor.close()
    return all_ok

def run_intelligent_migration():
    """Punto de entrada principal para la migración inteligente. Devuelve True si éxito, False si fallo."""
    logger.info("===========================================================")
    logger.info("--- INICIANDO MIGRACIÓN INTELIGENTE DE BASE DE DATOS ---")
    logger.info("===========================================================")
    
    ideal_schema = parse_sql_schema()
    if ideal_schema is None:
        logger.critical("MIGRACIÓN FALLIDA: No se pudo analizar el fichero 'schema.sql'. Revisar logs anteriores.")
        return False

    db_conn = None
    try:
        logger.info("Intentando conectar a la base de datos...")
        db_conn = get_connection()
        if db_conn is None or not db_conn.is_connected():
            logger.critical("MIGRACIÓN FALLIDA: No se pudo establecer conexión con la base de datos.")
            return False
        logger.info("Conexión a la base de datos establecida exitosamente.")

        cursor = db_conn.cursor(buffered=True)
        current_schema = get_current_schema(cursor)
        if current_schema is None:
            logger.critical("MIGRACIÓN FALLIDA: No se pudo obtener el esquema actual de la base de datos.")
            return False

        success = compare_and_apply_schema(db_conn, ideal_schema, current_schema)

        if success:
            logger.info("🎉 Migración completada sin errores. Confirmando todos los cambios (commit).")
            db_conn.commit()
            return True
        else:
            logger.error("Se detectaron errores durante la aplicación de cambios. Revirtiendo todo (rollback).")
            db_conn.rollback()
            return False

    except Exception as e:
        logger.critical(f"MIGRACIÓN FALLIDA: Ocurrió un error global inesperado: {e}", exc_info=True)
        if db_conn:
            try:
                db_conn.rollback()
                logger.info("Rollback realizado debido a error global.")
            except Exception as rb_e:
                logger.error(f"Error adicional durante el intento de rollback: {rb_e}")
        return False
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            logger.info("Conexión a la base de datos cerrada de forma segura.")
        logger.info("--- FIN DE LA MIGRACIÓN INTELIGENTE ---")

if __name__ == '__main__':
    # Esta sección permite ejecutar el script de forma independiente para depuración.
    logger.info("Ejecutando el gestor de migraciones en modo standalone...")
    migration_ok = run_intelligent_migration()
    if migration_ok:
        logger.info("Resultado del script standalone: ÉXITO")
        sys.exit(0)
    else:
        logger.error("Resultado del script standalone: FALLO")
        sys.exit(1)

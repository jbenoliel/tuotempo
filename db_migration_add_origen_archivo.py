#!/usr/bin/env python3
"""
Migración para añadir el campo origen_archivo a la tabla leads
y crear la tabla archivos_origen para referencia de ficheros.

Autor: Claude Code
Fecha: 2025-09-03
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import pymysql
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migration_origen_archivo.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def get_connection():
    """Establecer conexión con la base de datos Railway."""
    load_dotenv()
    
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQLHOST'),
            user=os.getenv('MYSQLUSER'),
            password=os.getenv('MYSQLPASSWORD'),
            database=os.getenv('MYSQLDATABASE'),
            port=int(os.getenv('MYSQLPORT')),
            charset='utf8mb4',
            autocommit=False
        )
        logger.info(f"[OK] Conectado a BD: {os.getenv('MYSQLDATABASE')}")
        return conn
    except Exception as e:
        logger.error(f"❌ Error conectando a BD: {e}")
        return None

def check_if_migration_needed(cursor):
    """Verificar si la migración es necesaria."""
    logger.info("🔍 Verificando si la migración es necesaria...")
    
    # Verificar si ya existe el campo origen_archivo
    cursor.execute("SHOW COLUMNS FROM leads LIKE 'origen_archivo'")
    origen_archivo_exists = cursor.fetchone() is not None
    
    # Verificar si ya existe la tabla archivos_origen
    cursor.execute("SHOW TABLES LIKE 'archivos_origen'")
    tabla_archivos_exists = cursor.fetchone() is not None
    
    logger.info(f"Campo 'origen_archivo' existe: {origen_archivo_exists}")
    logger.info(f"Tabla 'archivos_origen' existe: {tabla_archivos_exists}")
    
    return not origen_archivo_exists or not tabla_archivos_exists

def create_archivos_origen_table(cursor):
    """Crear la tabla archivos_origen para referencia de ficheros."""
    logger.info("[INFO] Creando tabla 'archivos_origen'...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS `archivos_origen` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `nombre_archivo` VARCHAR(255) NOT NULL UNIQUE COMMENT 'Nombre del archivo de origen',
        `descripcion` TEXT NULL COMMENT 'Descripción del archivo',
        `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación del registro',
        `total_registros` INT DEFAULT 0 COMMENT 'Total de registros importados desde este archivo',
        `usuario_creacion` VARCHAR(100) NULL COMMENT 'Usuario que realizó la importación',
        `activo` TINYINT(1) DEFAULT 1 COMMENT 'Flag para indicar si el archivo está activo',
        INDEX `idx_nombre_archivo` (`nombre_archivo`),
        INDEX `idx_fecha_creacion` (`fecha_creacion`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    COMMENT='Tabla de referencia para archivos de origen de datos'
    """
    
    cursor.execute(sql)
    logger.info("[OK] Tabla 'archivos_origen' creada exitosamente")

def add_origen_archivo_field(cursor):
    """Añadir el campo origen_archivo a la tabla leads."""
    logger.info("[INFO] Añadiendo campo 'origen_archivo' a tabla leads...")
    
    # Verificar si existe el campo lead_status para decidir dónde colocar el nuevo campo
    cursor.execute("SHOW COLUMNS FROM leads LIKE 'lead_status'")
    lead_status_exists = cursor.fetchone() is not None
    
    if lead_status_exists:
        # BD de producción con campo lead_status
        sql = """
        ALTER TABLE `leads` 
        ADD COLUMN `origen_archivo` VARCHAR(255) NULL 
        COMMENT 'Nombre del archivo de origen de los datos' 
        AFTER `lead_status`
        """
    else:
        # BD local sin campo lead_status - añadir al final
        sql = """
        ALTER TABLE `leads` 
        ADD COLUMN `origen_archivo` VARCHAR(255) NULL 
        COMMENT 'Nombre del archivo de origen de los datos'
        """
    
    cursor.execute(sql)
    logger.info("[OK] Campo 'origen_archivo' añadido exitosamente a tabla leads")

def create_foreign_key(cursor):
    """Crear índice y relación lógica (no FK física por rendimiento)."""
    logger.info("🔗 Creando índice para campo origen_archivo...")
    
    sql = """
    CREATE INDEX `idx_origen_archivo` ON `leads`(`origen_archivo`)
    """
    
    cursor.execute(sql)
    logger.info("✅ Índice creado para campo origen_archivo")

def insert_default_archivo_origen(cursor):
    """Insertar el registro por defecto para datos existentes."""
    logger.info("📥 Insertando archivo origen por defecto...")
    
    sql = """
    INSERT IGNORE INTO `archivos_origen` 
    (nombre_archivo, descripcion, usuario_creacion, total_registros) 
    VALUES 
    ('SEGURCAIXA_JULIO', 'Datos históricos de Segurcaixa del mes de julio', 'sistema', 0)
    """
    
    cursor.execute(sql)
    logger.info("✅ Archivo origen 'SEGURCAIXA_JULIO' insertado")

def update_existing_records(cursor):
    """Actualizar registros existentes con el archivo origen por defecto."""
    logger.info("🔄 Actualizando registros existentes con origen SEGURCAIXA_JULIO...")
    
    # Contar registros sin origen_archivo
    cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo IS NULL")
    count_null = cursor.fetchone()[0]
    logger.info(f"Registros a actualizar: {count_null}")
    
    if count_null > 0:
        sql = """
        UPDATE `leads` 
        SET `origen_archivo` = 'SEGURCAIXA_JULIO' 
        WHERE `origen_archivo` IS NULL
        """
        
        cursor.execute(sql)
        affected_rows = cursor.rowcount
        logger.info(f"✅ {affected_rows} registros actualizados con origen SEGURCAIXA_JULIO")
        
        # Actualizar contador en tabla archivos_origen
        cursor.execute("""
            UPDATE archivos_origen 
            SET total_registros = %s 
            WHERE nombre_archivo = 'SEGURCAIXA_JULIO'
        """, (affected_rows,))
        logger.info("✅ Contador de registros actualizado en archivos_origen")
    else:
        logger.info("ℹ️ No hay registros para actualizar")

def verify_migration(cursor):
    """Verificar que la migración se aplicó correctamente."""
    logger.info("🔍 Verificando migración...")
    
    # Verificar campo origen_archivo
    cursor.execute("SHOW COLUMNS FROM leads LIKE 'origen_archivo'")
    if cursor.fetchone():
        logger.info("✅ Campo 'origen_archivo' existe")
    else:
        logger.error("❌ Campo 'origen_archivo' NO existe")
        return False
    
    # Verificar tabla archivos_origen
    cursor.execute("SHOW TABLES LIKE 'archivos_origen'")
    if cursor.fetchone():
        logger.info("✅ Tabla 'archivos_origen' existe")
    else:
        logger.error("❌ Tabla 'archivos_origen' NO existe")
        return False
    
    # Verificar datos
    cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO'")
    count_segurcaixa = cursor.fetchone()[0]
    
    cursor.execute("SELECT total_registros FROM archivos_origen WHERE nombre_archivo = 'SEGURCAIXA_JULIO'")
    total_archivo = cursor.fetchone()[0]
    
    logger.info(f"✅ Registros con origen SEGURCAIXA_JULIO: {count_segurcaixa}")
    logger.info(f"✅ Total en archivos_origen: {total_archivo}")
    
    return True

def run_migration():
    """Ejecutar la migración completa."""
    logger.info("🚀 === INICIANDO MIGRACIÓN ORIGEN_ARCHIVO ===")
    start_time = datetime.now()
    
    conn = get_connection()
    if not conn:
        logger.error("❌ No se pudo conectar a la base de datos")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar si es necesario
        if not check_if_migration_needed(cursor):
            logger.info("ℹ️ La migración ya fue aplicada anteriormente")
            return True
        
        logger.info("📋 Ejecutando pasos de migración...")
        
        # Paso 1: Crear tabla archivos_origen
        create_archivos_origen_table(cursor)
        
        # Paso 2: Añadir campo origen_archivo a leads
        try:
            add_origen_archivo_field(cursor)
        except pymysql.Error as e:
            if "Duplicate column name" in str(e):
                logger.info("ℹ️ Campo 'origen_archivo' ya existe, continuando...")
            else:
                raise e
        
        # Paso 3: Crear índice
        try:
            create_foreign_key(cursor)
        except pymysql.Error as e:
            if "Duplicate key name" in str(e):
                logger.info("ℹ️ Índice 'idx_origen_archivo' ya existe, continuando...")
            else:
                raise e
        
        # Paso 4: Insertar archivo origen por defecto
        insert_default_archivo_origen(cursor)
        
        # Paso 5: Actualizar registros existentes
        update_existing_records(cursor)
        
        # Paso 6: Verificar migración
        if not verify_migration(cursor):
            logger.error("❌ La verificación de migración falló")
            return False
        
        # Confirmar cambios
        conn.commit()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"✅ === MIGRACIÓN COMPLETADA EN {duration.total_seconds():.2f}s ===")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()
        logger.info("🔌 Conexión cerrada")

if __name__ == "__main__":
    logger.info(f"Iniciando migración - Fecha: {datetime.now()}")
    success = run_migration()
    
    if success:
        logger.info("🎉 MIGRACIÓN EXITOSA")
        sys.exit(0)
    else:
        logger.error("💥 MIGRACIÓN FALLÓ")
        sys.exit(1)
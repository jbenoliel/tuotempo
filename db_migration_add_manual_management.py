"""
Migración para añadir campo de gestión manual de leads.
Fecha: 2025-01-22
Descripción: Añade campo manual_management para indicar que un lead se gestiona manualmente.
"""

import mysql.connector
from mysql.connector import Error
from db import get_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración para añadir campo de gestión manual."""
    
    # SQL para añadir el nuevo campo
    migration_queries = [
        """
        ALTER TABLE leads 
        ADD COLUMN manual_management BOOLEAN DEFAULT FALSE 
        COMMENT 'Indica si el lead se gestiona manualmente (no debe ser llamado automáticamente)'
        """,
        
        """
        CREATE INDEX idx_manual_management ON leads(manual_management)
        """
    ]
    
    # SQL para revertir la migración (rollback)
    rollback_queries = [
        "DROP INDEX idx_manual_management ON leads",
        "ALTER TABLE leads DROP COLUMN manual_management"
    ]
    
    connection = None
    try:
        connection = get_connection()
        if not connection:
            logger.error("❌ No se pudo establecer conexión con la base de datos")
            return False
            
        cursor = connection.cursor()
        
        # Verificar si el campo ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'leads' 
            AND COLUMN_NAME = 'manual_management'
        """)
        
        field_exists = cursor.fetchone()[0] > 0
        
        if field_exists:
            logger.info("✅ El campo 'manual_management' ya existe en la tabla 'leads'")
            return True
        
        logger.info("🚀 Ejecutando migración: añadir campo manual_management...")
        
        for i, query in enumerate(migration_queries, 1):
            try:
                cursor.execute(query)
                logger.info(f"✅ Consulta {i}/{len(migration_queries)} ejecutada correctamente")
            except Error as e:
                logger.error(f"❌ Error ejecutando consulta {i}: {e}")
                # Si falla, intentar rollback
                logger.info("🔄 Intentando rollback...")
                try:
                    for rollback_query in reversed(rollback_queries[:i]):
                        cursor.execute(rollback_query)
                    logger.info("✅ Rollback completado")
                except Error as rollback_error:
                    logger.error(f"❌ Error en rollback: {rollback_error}")
                return False
        
        connection.commit()
        
        # Verificar que la migración se ejecutó correctamente
        cursor.execute("DESCRIBE leads")
        columns = cursor.fetchall()
        manual_management_found = any('manual_management' in str(col) for col in columns)
        
        if manual_management_found:
            logger.info("✅ Migración completada exitosamente")
            logger.info("📋 Campo añadido: manual_management BOOLEAN DEFAULT FALSE")
            return True
        else:
            logger.error("❌ La migración no se completó correctamente")
            return False
            
    except Error as e:
        logger.error(f"❌ Error durante la migración: {e}")
        return False
        
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("🔒 Conexión a la base de datos cerrada")

def rollback_migration():
    """Revierte la migración (elimina el campo manual_management)."""
    
    connection = None
    try:
        connection = get_connection()
        if not connection:
            logger.error("❌ No se pudo establecer conexión con la base de datos")
            return False
            
        cursor = connection.cursor()
        
        # Verificar si el campo existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'leads' 
            AND COLUMN_NAME = 'manual_management'
        """)
        
        field_exists = cursor.fetchone()[0] > 0
        
        if not field_exists:
            logger.info("ℹ️ El campo 'manual_management' no existe, no hay nada que revertir")
            return True
        
        logger.info("🔄 Ejecutando rollback: eliminar campo manual_management...")
        
        # Eliminar índice y campo
        rollback_queries = [
            "DROP INDEX IF EXISTS idx_manual_management ON leads",
            "ALTER TABLE leads DROP COLUMN manual_management"
        ]
        
        for i, query in enumerate(rollback_queries, 1):
            try:
                cursor.execute(query)
                logger.info(f"✅ Rollback consulta {i}/{len(rollback_queries)} ejecutada")
            except Error as e:
                logger.error(f"❌ Error en rollback consulta {i}: {e}")
                return False
        
        connection.commit()
        logger.info("✅ Rollback completado exitosamente")
        return True
        
    except Error as e:
        logger.error(f"❌ Error durante el rollback: {e}")
        return False
        
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("🔒 Conexión a la base de datos cerrada")

if __name__ == "__main__":
    print("Migracion: Anadir campo de gestion manual")
    print("=" * 50)
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Ejecutando rollback...")
        success = rollback_migration()
    else:
        print("Ejecutando migracion...")
        success = run_migration()
    
    if success:
        print("Operacion completada exitosamente")
    else:
        print("La operacion fallo")
        sys.exit(1)
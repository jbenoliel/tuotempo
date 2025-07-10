"""
Migración para añadir campos relacionados con el sistema de llamadas automáticas de Pearl AI.
Fecha: 2025-07-09
Descripción: Añade campos para gestionar el estado y control de llamadas automáticas.
"""

import mysql.connector
from mysql.connector import Error
from db import get_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración para añadir campos de llamadas."""
    
    # SQL para añadir los nuevos campos
    migration_queries = [
        """
        ALTER TABLE leads 
        ADD COLUMN call_status ENUM(
            'no_selected', 
            'selected', 
            'calling', 
            'completed', 
            'error', 
            'busy', 
            'no_answer'
        ) DEFAULT 'no_selected' 
        COMMENT 'Estado actual de la llamada automática'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN call_priority INT DEFAULT 3 
        COMMENT 'Prioridad de llamada (1=Alta, 3=Normal, 5=Baja)'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN selected_for_calling BOOLEAN DEFAULT FALSE 
        COMMENT 'Flag para indicar si el lead está seleccionado para llamar'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN pearl_outbound_id VARCHAR(100) NULL 
        COMMENT 'ID de la campaña outbound de Pearl AI'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN last_call_attempt DATETIME NULL 
        COMMENT 'Fecha y hora del último intento de llamada'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN call_attempts_count INT DEFAULT 0 
        COMMENT 'Número de intentos de llamada realizados'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN call_error_message TEXT NULL 
        COMMENT 'Último mensaje de error en caso de fallo en la llamada'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN pearl_call_response TEXT NULL 
        COMMENT 'Respuesta completa de la API de Pearl AI'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN call_notes TEXT NULL 
        COMMENT 'Notas adicionales sobre la llamada'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP 
        COMMENT 'Timestamp de última actualización del registro'
        """
    ]
    
    # Crear índices para mejorar el rendimiento
    index_queries = [
        "CREATE INDEX idx_call_status ON leads(call_status)",
        "CREATE INDEX idx_selected_for_calling ON leads(selected_for_calling)",
        "CREATE INDEX idx_call_priority ON leads(call_priority)",
        "CREATE INDEX idx_last_call_attempt ON leads(last_call_attempt)",
        "CREATE INDEX idx_pearl_outbound_id ON leads(pearl_outbound_id)"
    ]
    
    conn = None
    try:
        # Conectar a la base de datos
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la base de datos")
            return False
            
        cursor = conn.cursor()
        logger.info("Iniciando migración de campos de llamadas...")
        
        # Ejecutar las consultas de migración
        for i, query in enumerate(migration_queries, 1):
            try:
                logger.info(f"Ejecutando migración {i}/{len(migration_queries)}...")
                cursor.execute(query)
                logger.info(f"✅ Migración {i} completada exitosamente")
            except Error as e:
                if "Duplicate column name" in str(e) or "duplicate column name" in str(e).lower():
                    logger.info(f"⚠️  Migración {i} ya aplicada (columna existe)")
                else:
                    logger.error(f"❌ Error en migración {i}: {e}")
                    return False
        
        # Ejecutar las consultas de índices
        logger.info("Creando índices...")
        for i, query in enumerate(index_queries, 1):
            try:
                cursor.execute(query)
                logger.info(f"✅ Índice {i} creado exitosamente")
            except Error as e:
                if "Duplicate key name" in str(e) or "duplicate key name" in str(e).lower():
                    logger.info(f"⚠️  Índice {i} ya existe")
                else:
                    logger.error(f"❌ Error creando índice {i}: {e}")
        
        # Confirmar cambios
        conn.commit()
        logger.info("🎉 ¡Migración completada exitosamente!")
        
        # Mostrar estructura actualizada
        cursor.execute("DESCRIBE leads")
        columns = cursor.fetchall()
        logger.info("📋 Estructura actualizada de la tabla 'leads':")
        for col in columns:
            if any(keyword in col[0] for keyword in ['call_', 'selected_for_calling', 'pearl_', 'updated_at']):
                logger.info(f"   🆕 {col[0]}: {col[1]} {col[2] if col[2] else ''}")
        
        return True
        
    except Error as e:
        logger.error(f"❌ Error durante la migración: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            logger.info("Conexión a la base de datos cerrada")

def rollback_migration():
    """Rollback de la migración (elimina los campos añadidos)."""
    
    rollback_queries = [
        "ALTER TABLE leads DROP COLUMN call_status",
        "ALTER TABLE leads DROP COLUMN call_priority",
        "ALTER TABLE leads DROP COLUMN selected_for_calling",
        "ALTER TABLE leads DROP COLUMN pearl_outbound_id",
        "ALTER TABLE leads DROP COLUMN last_call_attempt",
        "ALTER TABLE leads DROP COLUMN call_attempts_count",
        "ALTER TABLE leads DROP COLUMN call_error_message",
        "ALTER TABLE leads DROP COLUMN pearl_call_response",
        "ALTER TABLE leads DROP COLUMN call_notes",
        "ALTER TABLE leads DROP COLUMN updated_at"
    ]
    
    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la base de datos")
            return False
            
        cursor = conn.cursor()
        logger.info("Iniciando rollback de la migración...")
        
        for i, query in enumerate(rollback_queries, 1):
            try:
                cursor.execute(query)
                logger.info(f"✅ Rollback {i}/{len(rollback_queries)} completado")
            except Error as e:
                if "check that column/key exists" in str(e).lower() or "can't drop" in str(e).lower():
                    logger.info(f"⚠️  Rollback {i}: columna ya no existe")
                else:
                    logger.error(f"❌ Error en rollback {i}: {e}")
        
        conn.commit()
        logger.info("🔄 Rollback completado")
        return True
        
    except Error as e:
        logger.error(f"❌ Error durante el rollback: {e}")
        return False
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("🔄 Ejecutando rollback de la migración...")
        success = rollback_migration()
    else:
        print("🚀 Ejecutando migración de campos de llamadas...")
        success = run_migration()
    
    if success:
        print("✅ Operación completada exitosamente")
    else:
        print("❌ La operación falló")
    
    sys.exit(0 if success else 1)

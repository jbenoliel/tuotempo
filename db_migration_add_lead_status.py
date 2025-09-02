"""
Migración para añadir campo lead_status y configuración del scheduler.
Fecha: 2025-09-02
Descripción: Añade campo lead_status y tablas para el sistema de scheduler automático.
"""

import mysql.connector
from mysql.connector import Error
from db import get_connection
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración para añadir el sistema de scheduler."""
    
    # SQL para añadir el nuevo campo lead_status
    migration_queries = [
        """
        ALTER TABLE leads 
        ADD COLUMN lead_status ENUM('open', 'closed') DEFAULT 'open' 
        COMMENT 'Estado del lead: open (abierto para llamadas) o closed (cerrado definitivamente)'
        """,
        
        """
        ALTER TABLE leads 
        ADD COLUMN closure_reason VARCHAR(100) NULL 
        COMMENT 'Razón de cierre cuando lead_status = closed'
        """
    ]
    
    # Crear tabla call_schedule para gestionar las llamadas programadas
    table_queries = [
        """
        CREATE TABLE IF NOT EXISTS call_schedule (
            id INT PRIMARY KEY AUTO_INCREMENT,
            lead_id INT NOT NULL,
            scheduled_at DATETIME NOT NULL,
            attempt_number INT NOT NULL,
            status ENUM('pending', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
            last_outcome VARCHAR(50) NULL COMMENT 'Resultado del último intento: no_answer, busy, hang_up, etc.',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
            INDEX idx_scheduled_at (scheduled_at),
            INDEX idx_lead_status (lead_id, status),
            INDEX idx_status_scheduled (status, scheduled_at)
        ) COMMENT 'Programación automática de llamadas con scheduler'
        """,
        
        """
        CREATE TABLE IF NOT EXISTS scheduler_config (
            id INT PRIMARY KEY AUTO_INCREMENT,
            config_key VARCHAR(50) UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description TEXT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) COMMENT 'Configuración parametrizable del scheduler'
        """
    ]
    
    # Configuraciones por defecto del scheduler
    default_configs = [
        ('working_hours_start', '10:00', 'Hora de inicio de las llamadas (formato HH:MM)'),
        ('working_hours_end', '20:00', 'Hora de fin de las llamadas (formato HH:MM)'),
        ('reschedule_hours', '30', 'Horas a esperar antes de reprogramar una llamada'),
        ('max_attempts', '6', 'Número máximo de intentos antes de cerrar automáticamente'),
        ('closure_reasons', json.dumps({
            'no_answer': 'Ilocalizable',
            'hang_up': 'No colabora',
            'invalid_phone': 'Teléfono erróneo'
        }), 'Razones de cierre automático según el tipo de fallo'),
        ('working_days', json.dumps([1, 2, 3, 4, 5]), 'Días laborables (1=Lunes, 7=Domingo)')
    ]
    
    # Crear índices para mejorar el rendimiento
    index_queries = [
        "CREATE INDEX idx_lead_status ON leads(lead_status)",
        "CREATE INDEX idx_closure_reason ON leads(closure_reason)"
    ]
    
    conn = None
    try:
        # Conectar a la base de datos
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la base de datos")
            return False
            
        cursor = conn.cursor()
        logger.info("Iniciando migración del scheduler...")
        
        # Ejecutar las consultas de migración de campos
        for i, query in enumerate(migration_queries, 1):
            try:
                logger.info(f"Ejecutando migración de campos {i}/{len(migration_queries)}...")
                cursor.execute(query)
                logger.info(f"Migracion de campos {i} completada exitosamente")
            except Error as e:
                if "Duplicate column name" in str(e) or "duplicate column name" in str(e).lower():
                    logger.info(f"Migracion {i} ya aplicada (columna existe)")
                else:
                    logger.error(f"Error en migracion {i}: {e}")
                    return False
        
        # Ejecutar las consultas de creación de tablas
        for i, query in enumerate(table_queries, 1):
            try:
                logger.info(f"Creando tabla {i}/{len(table_queries)}...")
                cursor.execute(query)
                logger.info(f"Tabla {i} creada exitosamente")
            except Error as e:
                logger.error(f"Error creando tabla {i}: {e}")
                return False
        
        # Ejecutar las consultas de índices
        logger.info("Creando índices...")
        for i, query in enumerate(index_queries, 1):
            try:
                cursor.execute(query)
                logger.info(f"Indice {i} creado exitosamente")
            except Error as e:
                if "Duplicate key name" in str(e) or "duplicate key name" in str(e).lower():
                    logger.info(f"Indice {i} ya existe")
                else:
                    logger.error(f"Error creando indice {i}: {e}")
        
        # Insertar configuraciones por defecto
        logger.info("Insertando configuraciones por defecto del scheduler...")
        for config_key, config_value, description in default_configs:
            try:
                cursor.execute("""
                    INSERT INTO scheduler_config (config_key, config_value, description) 
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        description = VALUES(description),
                        updated_at = CURRENT_TIMESTAMP
                """, (config_key, config_value, description))
                logger.info(f"Configuracion '{config_key}' insertada/actualizada")
            except Error as e:
                logger.error(f"Error insertando configuracion '{config_key}': {e}")
        
        # Confirmar cambios
        conn.commit()
        logger.info("Migracion del scheduler completada exitosamente!")
        
        # Mostrar estructura actualizada
        cursor.execute("DESCRIBE leads")
        columns = cursor.fetchall()
        logger.info("Nuevos campos añadidos a la tabla 'leads':")
        for col in columns:
            if col[0] in ['lead_status', 'closure_reason']:
                logger.info(f"   {col[0]}: {col[1]} {col[2] if col[2] else ''}")
        
        # Mostrar configuraciones insertadas
        cursor.execute("SELECT config_key, config_value, description FROM scheduler_config")
        configs = cursor.fetchall()
        logger.info("Configuraciones del scheduler:")
        for config in configs:
            logger.info(f"   {config[0]}: {config[1]} - {config[2]}")
        
        return True
        
    except Error as e:
        logger.error(f"Error durante la migracion: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            logger.info("Conexión a la base de datos cerrada")

def rollback_migration():
    """Rollback de la migración (elimina los campos y tablas añadidas)."""
    
    rollback_queries = [
        "DROP TABLE IF EXISTS call_schedule",
        "DROP TABLE IF EXISTS scheduler_config",
        "ALTER TABLE leads DROP COLUMN IF EXISTS lead_status",
        "ALTER TABLE leads DROP COLUMN IF EXISTS closure_reason"
    ]
    
    conn = None
    try:
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la base de datos")
            return False
            
        cursor = conn.cursor()
        logger.info("Iniciando rollback de la migración del scheduler...")
        
        for i, query in enumerate(rollback_queries, 1):
            try:
                cursor.execute(query)
                logger.info(f"Rollback {i}/{len(rollback_queries)} completado")
            except Error as e:
                if "check that column/key exists" in str(e).lower() or "can't drop" in str(e).lower():
                    logger.info(f"Rollback {i}: elemento ya no existe")
                else:
                    logger.error(f"Error en rollback {i}: {e}")
        
        conn.commit()
        logger.info("Rollback completado")
        return True
        
    except Error as e:
        logger.error(f"Error durante el rollback: {e}")
        return False
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Ejecutando rollback de la migracion del scheduler...")
        success = rollback_migration()
    else:
        print("Ejecutando migracion del scheduler...")
        success = run_migration()
    
    if success:
        print("Operacion completada exitosamente")
    else:
        print("La operacion fallo")
    
    sys.exit(0 if success else 1)
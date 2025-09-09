#!/usr/bin/env python3
"""
Script para sincronizar la estructura de BD Railway con la local
Ejecuta todas las migraciones faltantes en Railway - VERSION CORREGIDA
"""

import mysql.connector
import logging
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    """Obtiene conexión a Railway usando MYSQL_URL"""
    mysql_url = os.getenv('MYSQL_URL')
    if not mysql_url:
        raise Exception("MYSQL_URL no está configurada")
    
    url = urlparse(mysql_url)
    config = {
        'host': url.hostname,
        'port': url.port or 3306,
        'user': url.username,
        'password': url.password,
        'database': url.path[1:]
    }
    
    logger.info(f"Conectando a Railway: {config['host']}:{config['port']} DB:{config['database']}")
    return mysql.connector.connect(**config)

def column_exists(cursor, table, column):
    """Verifica si una columna existe"""
    cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
    return cursor.fetchone() is not None

def index_exists(cursor, table, index_name):
    """Verifica si un índice existe"""
    cursor.execute(f"SHOW INDEX FROM {table} WHERE Key_name = '{index_name}'")
    return cursor.fetchone() is not None

def execute_sql_safe(cursor, sql, description):
    """Ejecuta SQL y maneja errores de manera segura"""
    try:
        cursor.execute(sql)
        logger.info(f"✅ {description}")
        return True
    except mysql.connector.Error as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["duplicate", "already exists", "can't drop"]):
            logger.info(f"⏭️ {description} - Ya existe o no necesario")
            return True
        else:
            logger.error(f"❌ {description} - Error: {e}")
            return False

def sync_railway_structure():
    """Sincroniza la estructura de Railway"""
    connection = None
    try:
        connection = get_railway_connection()
        cursor = connection.cursor()
        
        logger.info("=== INICIANDO SINCRONIZACION DE RAILWAY ===")
        
        # 1. Verificar si daemon_status existe
        cursor.execute("SHOW TABLES LIKE 'daemon_status'")
        if not cursor.fetchone():
            daemon_status_sql = """
            CREATE TABLE `daemon_status` (
                `id` int NOT NULL AUTO_INCREMENT,
                `daemon_name` varchar(100) NOT NULL UNIQUE,
                `is_running` tinyint(1) DEFAULT 0,
                `last_heartbeat` datetime DEFAULT NULL,
                `process_id` int DEFAULT NULL,
                `config_data` json DEFAULT NULL,
                `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
                `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            execute_sql_safe(cursor, daemon_status_sql, "Crear tabla daemon_status")
        else:
            logger.info("⏭️ Tabla daemon_status ya existe")
        
        # 2. Actualizar tabla pearl_calls
        logger.info("=== ACTUALIZANDO TABLA pearl_calls ===")
        
        # Primero recrear tabla pearl_calls con estructura correcta
        recreate_pearl_calls = """
        DROP TABLE IF EXISTS pearl_calls_backup;
        CREATE TABLE pearl_calls_backup AS SELECT * FROM pearl_calls;
        
        DROP TABLE pearl_calls;
        
        CREATE TABLE `pearl_calls` (
            `id` int NOT NULL AUTO_INCREMENT,
            `call_id` varchar(64) NOT NULL UNIQUE,
            `phone_number` varchar(20) NOT NULL,
            `call_time` datetime NOT NULL,
            `duration` int DEFAULT 0,
            `summary` text,
            `collected_info` json,
            `recording_url` varchar(512),
            `lead_id` int DEFAULT NULL,
            `status` varchar(50) DEFAULT NULL,
            `outbound_id` varchar(100) DEFAULT NULL,
            `start_time` datetime DEFAULT NULL,
            `end_time` datetime DEFAULT NULL,
            `outcome` varchar(50) DEFAULT NULL,
            `cost` decimal(10,4) DEFAULT NULL,
            `transcription` text,
            `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
            `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            INDEX `idx_phone` (`phone_number`),
            INDEX `idx_lead_id` (`lead_id`),
            CONSTRAINT `fk_pearl_calls_lead` FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        # Ejecutar cada comando por separado
        commands = recreate_pearl_calls.strip().split(';')
        for cmd in commands:
            cmd = cmd.strip()
            if cmd:
                execute_sql_safe(cursor, cmd, f"Recreando pearl_calls: {cmd[:50]}...")
        
        # 3. Actualizar campos específicos de tabla leads
        logger.info("=== ACTUALIZANDO TABLA leads ===")
        
        # Verificar y agregar campos faltantes uno por uno
        leads_updates = [
            ("reserva_automatica", "ALTER TABLE leads ADD COLUMN reserva_automatica tinyint(1) DEFAULT 0"),
            ("fecha_minima_reserva", "ALTER TABLE leads ADD COLUMN fecha_minima_reserva date DEFAULT NULL"),
            ("lead_status", "ALTER TABLE leads ADD COLUMN lead_status enum('open','closed') DEFAULT 'open'"),
            ("closure_reason", "ALTER TABLE leads ADD COLUMN closure_reason varchar(100) DEFAULT NULL")
        ]
        
        for column, sql in leads_updates:
            if not column_exists(cursor, 'leads', column):
                execute_sql_safe(cursor, sql, f"Añadir campo {column} a leads")
            else:
                logger.info(f"⏭️ Campo {column} ya existe en leads")
        
        # Cambiar tipo de cita de datetime a date
        execute_sql_safe(cursor, "ALTER TABLE leads MODIFY COLUMN cita date DEFAULT NULL", 
                        "Cambiar cita de datetime a date")
        
        # 4. Añadir índices faltantes
        logger.info("=== AÑADIENDO INDICES FALTANTES ===")
        
        indices_leads = [
            ("idx_call_status", "ALTER TABLE leads ADD INDEX idx_call_status (call_status)"),
            ("idx_call_priority", "ALTER TABLE leads ADD INDEX idx_call_priority (call_priority)"),
            ("idx_selected_for_calling", "ALTER TABLE leads ADD INDEX idx_selected_for_calling (selected_for_calling)"),
            ("idx_pearl_outbound_id", "ALTER TABLE leads ADD INDEX idx_pearl_outbound_id (pearl_outbound_id)"),
            ("idx_last_call_attempt", "ALTER TABLE leads ADD INDEX idx_last_call_attempt (last_call_attempt)"),
            ("idx_lead_status", "ALTER TABLE leads ADD INDEX idx_lead_status (lead_status)"),
            ("idx_closure_reason", "ALTER TABLE leads ADD INDEX idx_closure_reason (closure_reason)"),
            ("idx_origen_archivo", "ALTER TABLE leads ADD INDEX idx_origen_archivo (origen_archivo)"),
            ("idx_manual_management", "ALTER TABLE leads ADD INDEX idx_manual_management (manual_management)")
        ]
        
        for index_name, sql in indices_leads:
            if not index_exists(cursor, 'leads', index_name):
                execute_sql_safe(cursor, sql, f"Añadir índice {index_name}")
            else:
                logger.info(f"⏭️ Índice {index_name} ya existe")
        
        # 5. Limpiar usuarios tabla - eliminar campos que no pertenecen
        logger.info("=== LIMPIANDO TABLA usuarios ===")
        
        # Obtener lista de columnas actuales de usuarios
        cursor.execute("SHOW COLUMNS FROM usuarios")
        current_columns = [col[0] for col in cursor.fetchall()]
        
        # Campos que DEBEN mantenerse en usuarios
        valid_user_columns = {
            'id', 'username', 'password_hash', 'creado_en', 'email', 'is_admin', 
            'is_active', 'email_verified', 'created_at', 'reset_token', 'reset_token_expiry',
            'updated_at'
        }
        
        # Eliminar campos que no pertenecen a usuarios
        for column in current_columns:
            if column not in valid_user_columns:
                sql = f"ALTER TABLE usuarios DROP COLUMN {column}"
                execute_sql_safe(cursor, sql, f"Eliminar campo {column} de usuarios")
        
        # 6. Actualizar scheduler_config
        execute_sql_safe(cursor, 
            "ALTER TABLE scheduler_config MODIFY COLUMN description text DEFAULT NULL",
            "Actualizar campo description en scheduler_config")
        
        connection.commit()
        logger.info("SINCRONIZACION COMPLETADA - Railway actualizado")
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    try:
        sync_railway_structure()
        print("\nRailway sincronizado exitosamente!")
        print("La estructura de Railway ahora coincide con la local.")
    except Exception as e:
        print(f"\nError en sincronización: {e}")
        exit(1)
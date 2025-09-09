#!/usr/bin/env python3
"""
Script para sincronizar la estructura de BD Railway con la local
Ejecuta todas las migraciones faltantes en Railway
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

def execute_sql(cursor, sql, description):
    """Ejecuta SQL y maneja errores"""
    try:
        cursor.execute(sql)
        logger.info(f"✅ {description}")
        return True
    except mysql.connector.Error as e:
        if "Duplicate column" in str(e) or "already exists" in str(e):
            logger.info(f"⏭️ {description} - Ya existe")
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
        
        logger.info("=== INICIANDO SINCRONIZACIÓN DE RAILWAY ===")
        
        # 1. Crear tabla daemon_status (falta en Railway)
        daemon_status_sql = """
        CREATE TABLE IF NOT EXISTS `daemon_status` (
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
        execute_sql(cursor, daemon_status_sql, "Crear tabla daemon_status")
        
        # 2. Actualizar tabla pearl_calls - eliminar campos incompatibles y añadir los correctos
        logger.info("=== ACTUALIZANDO TABLA pearl_calls ===")
        
        # Eliminar campos incompatibles de Railway
        remove_fields = [
            "ALTER TABLE pearl_calls DROP COLUMN IF EXISTS usuario_id",
            "ALTER TABLE pearl_calls DROP COLUMN IF EXISTS fecha", 
            "ALTER TABLE pearl_calls DROP COLUMN IF EXISTS archivo",
            "ALTER TABLE pearl_calls DROP COLUMN IF EXISTS registros_importados",
            "ALTER TABLE pearl_calls DROP COLUMN IF EXISTS resultado",
            "ALTER TABLE pearl_calls DROP COLUMN IF EXISTS mensaje"
        ]
        
        for sql in remove_fields:
            execute_sql(cursor, sql, f"Eliminando campo incompatible")
        
        # Añadir campos faltantes de la estructura local
        add_fields = [
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS status varchar(50) DEFAULT NULL",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS outbound_id varchar(100) DEFAULT NULL",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS start_time datetime DEFAULT NULL",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS end_time datetime DEFAULT NULL", 
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS outcome varchar(50) DEFAULT NULL",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS cost decimal(10,4) DEFAULT NULL",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS transcription text DEFAULT NULL",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS created_at timestamp DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE pearl_calls ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        ]
        
        for sql in add_fields:
            execute_sql(cursor, sql, f"Añadiendo campo faltante a pearl_calls")
        
        # 3. Actualizar tabla leads - añadir campos faltantes
        logger.info("=== ACTUALIZANDO TABLA leads ===")
        
        leads_fields = [
            "ALTER TABLE leads MODIFY COLUMN cita date DEFAULT NULL",  # Cambiar de datetime a date
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS reserva_automatica tinyint(1) DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS fecha_minima_reserva date DEFAULT NULL",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS preferencia_horario enum('mañana','tarde') DEFAULT 'mañana'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_status enum('open','closed') DEFAULT 'open'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS closure_reason varchar(100) DEFAULT NULL",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS origen_archivo varchar(255) DEFAULT NULL",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS manual_management tinyint(1) DEFAULT 0"
        ]
        
        for sql in leads_fields:
            execute_sql(cursor, sql, f"Actualizando campo en leads")
        
        # 4. Añadir índices faltantes
        logger.info("=== AÑADIENDO ÍNDICES FALTANTES ===")
        
        indices = [
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_call_status (call_status)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_call_priority (call_priority)", 
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_selected_for_calling (selected_for_calling)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_pearl_outbound_id (pearl_outbound_id)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_last_call_attempt (last_call_attempt)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_lead_status (lead_status)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_closure_reason (closure_reason)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_origen_archivo (origen_archivo)",
            "ALTER TABLE leads ADD INDEX IF NOT EXISTS idx_manual_management (manual_management)"
        ]
        
        for sql in indices:
            execute_sql(cursor, sql, f"Añadiendo índice")
        
        # 5. Limpiar tabla usuarios - eliminar campos duplicados de leads
        logger.info("=== LIMPIANDO TABLA usuarios ===")
        
        usuarios_cleanup = [
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS nombre",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS apellidos", 
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS telefono",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS telefono2",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS nif",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS fecha_nacimiento",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS sexo",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS poliza",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS segmento",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS certificado",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS delegacion",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS clinica_id",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS nombre_clinica",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS direccion_clinica",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS codigo_postal",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS ciudad",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS area_id",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS match_source",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS match_confidence",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS orden",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS ultimo_estado",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS resultado_llamada",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS status_level_1",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS status_level_2",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS cita",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS conPack",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS hora_rellamada",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS razon_vuelta_a_llamar",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS razon_no_interes",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS error_tecnico",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_id",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_time",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_duration",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_summary",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_recording_url",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_status",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_priority",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS selected_for_calling",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS pearl_outbound_id",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS last_call_attempt",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_attempts_count",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_error_message",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS pearl_call_response",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS call_notes"
        ]
        
        for sql in usuarios_cleanup:
            execute_sql(cursor, sql, f"Limpiando usuarios")
        
        # 6. Actualizar scheduler_config
        execute_sql(cursor, 
            "ALTER TABLE scheduler_config CHANGE COLUMN description description text DEFAULT NULL",
            "Actualizar campo description en scheduler_config")
        
        connection.commit()
        logger.info("✅ SINCRONIZACIÓN COMPLETADA - Railway actualizado")
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización: {e}")
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
        print("\n🎉 ¡Railway sincronizado exitosamente!")
        print("La estructura de Railway ahora coincide con la local.")
    except Exception as e:
        print(f"\n💥 Error en sincronización: {e}")
        exit(1)
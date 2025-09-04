"""
Script de migración para actualizar la base de datos local (pruebas)
con todos los campos y tablas necesarios para el sistema completo.

Este script añade:
1. Campos faltantes en tabla leads
2. Tablas del sistema de scheduler
3. Configuración inicial del scheduler
"""

import mysql.connector
import json
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_local_connection():
    """Conecta a la base de datos local."""
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Escogido00&Madrid',
        database='Segurcaixa',
        port=3306,
        auth_plugin='mysql_native_password'
    )

def migrate_leads_table(cursor):
    """Añade campos faltantes a la tabla leads."""
    logger.info("=== MIGRANDO TABLA LEADS ===")
    
    migrations = [
        {
            'campo': 'preferencia_horario',
            'sql': "ALTER TABLE leads ADD COLUMN preferencia_horario ENUM('mañana','tarde') DEFAULT NULL COMMENT 'Preferencia de horario del paciente'",
            'descripcion': 'Campo para preferenciaMT (MORNING/AFTERNOON)'
        },
        {
            'campo': 'fecha_minima_reserva', 
            'sql': "ALTER TABLE leads ADD COLUMN fecha_minima_reserva DATE DEFAULT NULL COMMENT 'Fecha mínima deseada por el paciente'",
            'descripcion': 'Campo para preferenciaFecha'
        },
        {
            'campo': 'lead_status',
            'sql': "ALTER TABLE leads ADD COLUMN lead_status ENUM('open','closed') DEFAULT 'open' COMMENT 'Estado del lead (abierto/cerrado)'",
            'descripcion': 'Control de estado del lead'
        },
        {
            'campo': 'closure_reason',
            'sql': "ALTER TABLE leads ADD COLUMN closure_reason VARCHAR(100) DEFAULT NULL COMMENT 'Razón de cierre del lead'", 
            'descripcion': 'Razón específica de cierre'
        }
    ]
    
    for migration in migrations:
        try:
            # Verificar si el campo ya existe
            cursor.execute("DESCRIBE leads")
            existing_columns = [col[0] for col in cursor.fetchall()]
            
            if migration['campo'] not in existing_columns:
                cursor.execute(migration['sql'])
                logger.info(f"✅ Añadido campo {migration['campo']}: {migration['descripcion']}")
            else:
                logger.info(f"⚠️  Campo {migration['campo']} ya existe, saltando...")
                
        except Exception as e:
            logger.error(f"❌ Error añadiendo campo {migration['campo']}: {e}")

def create_scheduler_tables(cursor):
    """Crea las tablas del sistema de scheduler."""
    logger.info("=== CREANDO TABLAS DEL SCHEDULER ===")
    
    # Tabla scheduler_config
    scheduler_config_sql = """
    CREATE TABLE IF NOT EXISTS scheduler_config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        config_key VARCHAR(50) NOT NULL UNIQUE,
        config_value TEXT NOT NULL,
        descripcion VARCHAR(255) DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_config_key (config_key)
    ) ENGINE=InnoDB COMMENT='Configuración del sistema de scheduler automático'
    """
    
    # Tabla call_schedule  
    call_schedule_sql = """
    CREATE TABLE IF NOT EXISTS call_schedule (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lead_id INT NOT NULL,
        scheduled_at DATETIME NOT NULL,
        attempt_number INT NOT NULL DEFAULT 1,
        status ENUM('pending', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
        last_outcome VARCHAR(50) DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_scheduled_at (scheduled_at),
        INDEX idx_status (status),
        INDEX idx_lead_id (lead_id),
        FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
    ) ENGINE=InnoDB COMMENT='Programación automática de llamadas'
    """
    
    try:
        cursor.execute(scheduler_config_sql)
        logger.info("✅ Tabla scheduler_config creada")
        
        cursor.execute(call_schedule_sql)
        logger.info("✅ Tabla call_schedule creada")
        
    except Exception as e:
        logger.error(f"❌ Error creando tablas del scheduler: {e}")

def insert_scheduler_config(cursor):
    """Inserta la configuración inicial del scheduler."""
    logger.info("=== CONFIGURANDO SCHEDULER INICIAL ===")
    
    configs = [
        {
            'key': 'max_attempts',
            'value': '6',
            'descripcion': 'Máximo número de intentos antes de cerrar automáticamente'
        },
        {
            'key': 'reschedule_hours', 
            'value': '30',
            'descripcion': 'Horas de espera antes de reprogramar una llamada'
        },
        {
            'key': 'working_hours_start',
            'value': '10:00',
            'descripcion': 'Hora de inicio del horario laboral'
        },
        {
            'key': 'working_hours_end',
            'value': '20:00', 
            'descripcion': 'Hora de fin del horario laboral'
        },
        {
            'key': 'working_days',
            'value': json.dumps([1, 2, 3, 4, 5]),
            'descripcion': 'Días laborables (1=Lunes, 7=Domingo)'
        },
        {
            'key': 'closure_reasons',
            'value': json.dumps({
                'no_answer': 'Ilocalizable',
                'hang_up': 'No colabora', 
                'invalid_phone': 'Telefono erroneo',
                'max_attempts': 'No útil'
            }),
            'descripcion': 'Mapeo de razones de cierre automático'
        }
    ]
    
    for config in configs:
        try:
            # Verificar si ya existe
            cursor.execute("SELECT COUNT(*) FROM scheduler_config WHERE config_key = %s", (config['key'],))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                cursor.execute("""
                    INSERT INTO scheduler_config (config_key, config_value, descripcion)
                    VALUES (%s, %s, %s)
                """, (config['key'], config['value'], config['descripcion']))
                logger.info(f"✅ Configuración añadida: {config['key']} = {config['value']}")
            else:
                logger.info(f"⚠️  Configuración {config['key']} ya existe, saltando...")
                
        except Exception as e:
            logger.error(f"❌ Error añadiendo configuración {config['key']}: {e}")

def create_archivos_origen_table(cursor):
    """Crea la tabla archivos_origen si no existe."""
    logger.info("=== VERIFICANDO TABLA ARCHIVOS_ORIGEN ===")
    
    archivos_origen_sql = """
    CREATE TABLE IF NOT EXISTS archivos_origen (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre_archivo VARCHAR(255) NOT NULL UNIQUE,
        descripcion TEXT DEFAULT NULL,
        total_registros INT DEFAULT 0,
        usuario_creacion VARCHAR(100) DEFAULT NULL,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        activo BOOLEAN DEFAULT TRUE,
        INDEX idx_nombre_archivo (nombre_archivo),
        INDEX idx_activo (activo)
    ) ENGINE=InnoDB COMMENT='Control de archivos importados'
    """
    
    try:
        cursor.execute(archivos_origen_sql)
        logger.info("✅ Tabla archivos_origen verificada/creada")
    except Exception as e:
        logger.error(f"❌ Error con tabla archivos_origen: {e}")

def main():
    """Ejecuta todas las migraciones."""
    logger.info("🚀 INICIANDO MIGRACIÓN DE BASE DE DATOS LOCAL")
    
    try:
        conn = get_local_connection()
        cursor = conn.cursor()
        
        # Ejecutar migraciones
        migrate_leads_table(cursor)
        create_scheduler_tables(cursor)
        create_archivos_origen_table(cursor)
        insert_scheduler_config(cursor)
        
        # Confirmar cambios
        conn.commit()
        logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        
        # Verificar resultado final
        logger.info("=== VERIFICACIÓN FINAL ===")
        cursor.execute("DESCRIBE leads")
        columns = cursor.fetchall()
        
        campos_importantes = ['status_level_1', 'status_level_2', 'call_attempts_count', 
                             'preferencia_horario', 'fecha_minima_reserva', 'lead_status', 'closure_reason']
        
        logger.info("Campos en tabla leads:")
        for campo in campos_importantes:
            found = any(col[0] == campo for col in columns)
            status = "✅" if found else "❌"
            logger.info(f"  {status} {campo}")
        
        # Verificar tablas
        cursor.execute("SHOW TABLES LIKE 'scheduler_config'")
        scheduler_exists = cursor.fetchone() is not None
        
        cursor.execute("SHOW TABLES LIKE 'call_schedule'")  
        schedule_exists = cursor.fetchone() is not None
        
        logger.info("Tablas del sistema:")
        logger.info(f"  {'✅' if scheduler_exists else '❌'} scheduler_config")
        logger.info(f"  {'✅' if schedule_exists else '❌'} call_schedule")
        
        if scheduler_exists:
            cursor.execute("SELECT COUNT(*) FROM scheduler_config")
            config_count = cursor.fetchone()[0]
            logger.info(f"  📊 Configuraciones del scheduler: {config_count}")
            
    except Exception as e:
        logger.error(f"❌ ERROR EN MIGRACIÓN: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
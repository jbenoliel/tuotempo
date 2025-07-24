#!/usr/bin/env python3
"""
Sistema de Monitoreo del Daemon de Reservas Automáticas
======================================================

Este módulo proporciona funcionalidades para monitorear el estado del daemon
de reservas automáticas y detectar si no está funcionando correctamente.

Funcionalidades:
- Registro de heartbeat del daemon
- Verificación de estado del daemon
- Alertas si el daemon no responde
- Endpoint de healthcheck
- Dashboard de estado
"""

import mysql.connector
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import settings

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_DATABASE,
    'ssl_disabled': True,
    'autocommit': True,
    'charset': 'utf8mb4',
    'use_unicode': True
}

class DaemonMonitor:
    """Clase para monitorear el estado del daemon de reservas automáticas"""
    
    def __init__(self):
        self.daemon_status = {
            'is_running': False,
            'last_heartbeat': None,
            'last_cycle_start': None,
            'last_cycle_end': None,
            'last_cycle_duration': None,
            'leads_processed': 0,
            'reservations_successful': 0,
            'reservations_failed': 0,
            'error_count': 0,
            'last_error': None
        }
        self.lock = threading.Lock()
    
    def get_db_connection(self):
        """Establece conexión con la base de datos MySQL"""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            return connection
        except mysql.connector.Error as err:
            logger.error(f"Error conectando a MySQL: {err}")
            # Si falla con SSL, intentar sin SSL
            if 'SSL' in str(err) or '2026' in str(err):
                try:
                    logger.info("Intentando conexión sin SSL...")
                    config_no_ssl = DB_CONFIG.copy()
                    config_no_ssl['ssl_disabled'] = True
                    connection = mysql.connector.connect(**config_no_ssl)
                    return connection
                except mysql.connector.Error as err2:
                    logger.error(f"Error conectando sin SSL: {err2}")
            return None
    
    def create_daemon_status_table(self):
        """Crea la tabla para almacenar el estado del daemon si no existe"""
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Crear tabla de estado del daemon
            create_table_query = """
            CREATE TABLE IF NOT EXISTS daemon_status (
                id INT AUTO_INCREMENT PRIMARY KEY,
                daemon_name VARCHAR(100) NOT NULL,
                is_running BOOLEAN DEFAULT FALSE,
                last_heartbeat DATETIME NULL,
                last_cycle_start DATETIME NULL,
                last_cycle_end DATETIME NULL,
                last_cycle_duration DECIMAL(10,2) NULL,
                leads_processed INT DEFAULT 0,
                reservations_successful INT DEFAULT 0,
                reservations_failed INT DEFAULT 0,
                error_count INT DEFAULT 0,
                last_error TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_daemon_name (daemon_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_table_query)
            conn.commit()
            
            logger.info("Tabla daemon_status creada/verificada exitosamente")
            return True
            
        except mysql.connector.Error as err:
            logger.error(f"Error creando tabla daemon_status: {err}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def update_heartbeat(self):
        """Actualiza el heartbeat del daemon en la base de datos"""
        with self.lock:
            self.daemon_status['last_heartbeat'] = datetime.now()
            self.daemon_status['is_running'] = True
        
        # Actualizar en base de datos
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Insertar o actualizar estado del daemon
            upsert_query = """
            INSERT INTO daemon_status (
                daemon_name, is_running, last_heartbeat, 
                last_cycle_start, last_cycle_end, last_cycle_duration,
                leads_processed, reservations_successful, reservations_failed,
                error_count, last_error
            ) VALUES (
                'reservas_automaticas', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                is_running = VALUES(is_running),
                last_heartbeat = VALUES(last_heartbeat),
                last_cycle_start = VALUES(last_cycle_start),
                last_cycle_end = VALUES(last_cycle_end),
                last_cycle_duration = VALUES(last_cycle_duration),
                leads_processed = VALUES(leads_processed),
                reservations_successful = VALUES(reservations_successful),
                reservations_failed = VALUES(reservations_failed),
                error_count = VALUES(error_count),
                last_error = VALUES(last_error),
                updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(upsert_query, (
                self.daemon_status['is_running'],
                self.daemon_status['last_heartbeat'],
                self.daemon_status['last_cycle_start'],
                self.daemon_status['last_cycle_end'],
                self.daemon_status['last_cycle_duration'],
                self.daemon_status['leads_processed'],
                self.daemon_status['reservations_successful'],
                self.daemon_status['reservations_failed'],
                self.daemon_status['error_count'],
                self.daemon_status['last_error']
            ))
            
            conn.commit()
            return True
            
        except mysql.connector.Error as err:
            logger.error(f"Error actualizando heartbeat: {err}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def start_cycle(self):
        """Marca el inicio de un ciclo de procesamiento"""
        with self.lock:
            self.daemon_status['last_cycle_start'] = datetime.now()
            self.daemon_status['last_cycle_end'] = None
        
        logger.info(f"[DAEMON-MONITOR] Ciclo iniciado: {self.daemon_status['last_cycle_start']}")
        self.update_heartbeat()
    
    def end_cycle(self, leads_processed=0, reservations_successful=0, reservations_failed=0):
        """Marca el final de un ciclo de procesamiento"""
        with self.lock:
            self.daemon_status['last_cycle_end'] = datetime.now()
            
            if self.daemon_status['last_cycle_start']:
                duration = (self.daemon_status['last_cycle_end'] - self.daemon_status['last_cycle_start']).total_seconds()
                self.daemon_status['last_cycle_duration'] = duration
            
            self.daemon_status['leads_processed'] = leads_processed
            self.daemon_status['reservations_successful'] = reservations_successful
            self.daemon_status['reservations_failed'] = reservations_failed
        
        logger.info(f"[DAEMON-MONITOR] Ciclo completado: {self.daemon_status['last_cycle_end']}, "
                   f"Duración: {self.daemon_status['last_cycle_duration']:.2f}s, "
                   f"Leads: {leads_processed}, Exitosas: {reservations_successful}, Fallidas: {reservations_failed}")
        
        self.update_heartbeat()
    
    def log_error(self, error_message):
        """Registra un error del daemon"""
        with self.lock:
            self.daemon_status['error_count'] += 1
            self.daemon_status['last_error'] = f"{datetime.now().isoformat()}: {error_message}"
        
        logger.error(f"[DAEMON-MONITOR] Error registrado: {error_message}")
        self.update_heartbeat()
    
    def get_status(self):
        """Obtiene el estado actual del daemon"""
        with self.lock:
            return self.daemon_status.copy()
    
    def get_status_from_db(self):
        """Obtiene el estado del daemon desde la base de datos"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
            SELECT * FROM daemon_status 
            WHERE daemon_name = 'reservas_automaticas'
            ORDER BY updated_at DESC 
            LIMIT 1
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                # Convertir datetime a string para JSON
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
            
            return result
            
        except mysql.connector.Error as err:
            logger.error(f"Error obteniendo estado desde BD: {err}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def is_daemon_healthy(self, max_silence_minutes=60):
        """Verifica si el daemon está saludable basado en el último heartbeat"""
        status = self.get_status_from_db()
        
        if not status:
            logger.warning("[DAEMON-MONITOR] No se pudo obtener estado del daemon desde BD")
            return False, "No se pudo obtener estado del daemon"
        
        if not status.get('is_running'):
            return False, "Daemon marcado como no ejecutándose"
        
        last_heartbeat_str = status.get('last_heartbeat')
        if not last_heartbeat_str:
            return False, "No hay registro de heartbeat"
        
        try:
            # Convertir string ISO a datetime
            last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace('Z', '+00:00'))
            if last_heartbeat.tzinfo is None:
                last_heartbeat = last_heartbeat.replace(tzinfo=None)
            else:
                last_heartbeat = last_heartbeat.replace(tzinfo=None)
            
            time_since_heartbeat = datetime.now() - last_heartbeat
            
            if time_since_heartbeat > timedelta(minutes=max_silence_minutes):
                return False, f"Último heartbeat hace {time_since_heartbeat.total_seconds()/60:.1f} minutos"
            
            return True, f"Daemon saludable, último heartbeat hace {time_since_heartbeat.total_seconds()/60:.1f} minutos"
            
        except Exception as e:
            logger.error(f"Error procesando heartbeat: {e}")
            return False, f"Error procesando heartbeat: {e}"
    
    def mark_daemon_stopped(self):
        """Marca el daemon como detenido"""
        with self.lock:
            self.daemon_status['is_running'] = False
        
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            update_query = """
            UPDATE daemon_status 
            SET is_running = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE daemon_name = 'reservas_automaticas'
            """
            
            cursor.execute(update_query)
            conn.commit()
            
            logger.info("[DAEMON-MONITOR] Daemon marcado como detenido")
            return True
            
        except mysql.connector.Error as err:
            logger.error(f"Error marcando daemon como detenido: {err}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

# Instancia global del monitor
daemon_monitor = DaemonMonitor()

def initialize_daemon_monitor():
    """Inicializa el sistema de monitoreo del daemon"""
    logger.info("[DAEMON-MONITOR] Inicializando sistema de monitoreo...")
    
    if daemon_monitor.create_daemon_status_table():
        logger.info("[DAEMON-MONITOR] Sistema de monitoreo inicializado correctamente")
        return True
    else:
        logger.error("[DAEMON-MONITOR] Error inicializando sistema de monitoreo")
        return False

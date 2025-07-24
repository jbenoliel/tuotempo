#!/usr/bin/env python3
"""
Script de configuración para Railway - Reservas Automáticas
==========================================================

Este script configura y ejecuta el sistema de reservas automáticas en Railway.
Maneja la migración de base de datos y el daemon de procesamiento.

Uso en Railway:
- Como servicio separado: python railway_reservas_setup.py
- Como parte del servicio principal: importar y usar las funciones
"""

import os
import sys
import logging
import time
import threading
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def verify_environment():
    """
    Verifica que todas las variables de entorno necesarias estén configuradas
    """
    logger.info("=== Verificando configuración de entorno ===")
    
    required_vars = [
        'MYSQLHOST', 'MYSQLUSER', 'MYSQLPASSWORD', 'MYSQLDATABASE', 'MYSQLPORT',
        'TUOTEMPO_API_BASE_URL', 'TUOTEMPO_API_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            logger.error(f"❌ Variable de entorno faltante: {var}")
        else:
            logger.info(f"✅ Variable configurada: {var}")
    
    if missing_vars:
        logger.critical(f"Faltan variables de entorno críticas: {missing_vars}")
        logger.critical("El sistema de reservas automáticas no puede funcionar sin estas variables.")
        return False
    
    logger.info("✅ Todas las variables de entorno están configuradas")
    return True

def run_database_migration():
    """
    Ejecuta la migración de base de datos para asegurar que los campos
    de reservas automáticas estén disponibles
    """
    logger.info("=== Ejecutando migración de base de datos ===")
    
    try:
        # Importar el sistema de migración existente
        from db_schema_manager import run_intelligent_migration
        
        logger.info("Iniciando migración inteligente basada en schema.sql...")
        
        if run_intelligent_migration():
            logger.info("✅ Migración de base de datos completada exitosamente")
            return True
        else:
            logger.error("❌ La migración de base de datos falló")
            return False
            
    except ImportError as e:
        logger.error(f"❌ No se pudo importar el sistema de migración: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        return False

def test_database_connection():
    """
    Prueba la conexión a la base de datos y verifica que los campos
    de reservas automáticas estén disponibles
    """
    logger.info("=== Probando conexión a base de datos ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        if not conn:
            logger.error("❌ No se pudo conectar a la base de datos")
            return False
        
        cursor = conn.cursor()
        
        # Verificar que la tabla leads tenga los campos necesarios
        cursor.execute("DESCRIBE leads")
        columns = [row[0] for row in cursor.fetchall()]
        
        required_columns = ['reserva_automatica', 'preferencia_horario', 'fecha_minima_reserva']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"❌ Faltan columnas en la tabla leads: {missing_columns}")
            logger.error("La migración de base de datos no se completó correctamente")
            return False
        
        logger.info("✅ Todos los campos de reservas automáticas están disponibles")
        
        # Probar una consulta simple
        cursor.execute("SELECT COUNT(*) FROM leads WHERE reserva_automatica = TRUE")
        count = cursor.fetchone()[0]
        logger.info(f"✅ Encontrados {count} leads marcados para reserva automática")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al probar la conexión a base de datos: {e}")
        return False

def start_reservation_daemon():
    """
    Inicia el daemon de procesamiento de reservas automáticas
    """
    logger.info("=== Iniciando daemon de reservas automáticas ===")
    
    try:
        from procesador_reservas_automaticas import ProcesadorReservasAutomaticas
        
        procesador = ProcesadorReservasAutomaticas()
        
        # Configurar intervalo desde variable de entorno (por defecto 30 minutos)
        interval_minutes = int(os.getenv('RESERVAS_INTERVAL_MINUTES', '30'))
        logger.info(f"Intervalo configurado: {interval_minutes} minutos")
        
        logger.info("🚀 Daemon de reservas automáticas iniciado")
        
        while True:
            try:
                start_time = datetime.now()
                logger.info(f"--- Iniciando ciclo de procesamiento: {start_time} ---")
                
                procesador.procesar_reservas_automaticas()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"--- Ciclo completado en {duration:.2f} segundos ---")
                
                logger.info(f"⏰ Esperando {interval_minutes} minutos hasta el próximo procesamiento...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Deteniendo daemon por interrupción del usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error en el ciclo de procesamiento: {e}")
                logger.info("⏰ Esperando 5 minutos antes de reintentar...")
                time.sleep(300)  # Esperar 5 minutos antes de reintentar
                
    except Exception as e:
        logger.error(f"❌ Error fatal al iniciar el daemon: {e}")
        sys.exit(1)

def run_single_processing():
    """
    Ejecuta un solo ciclo de procesamiento de reservas automáticas
    (útil para testing o ejecución manual)
    """
    logger.info("=== Ejecutando procesamiento único ===")
    
    try:
        from procesador_reservas_automaticas import ProcesadorReservasAutomaticas
        
        procesador = ProcesadorReservasAutomaticas()
        procesador.procesar_reservas_automaticas()
        
        logger.info("✅ Procesamiento único completado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en el procesamiento único: {e}")
        return False

def main():
    """
    Función principal para Railway
    """
    logger.info("🚀 Iniciando sistema de reservas automáticas en Railway")
    
    # Verificar configuración
    if not verify_environment():
        logger.critical("❌ Configuración de entorno inválida. Abortando.")
        sys.exit(1)
    
    # Ejecutar migración de base de datos
    if not run_database_migration():
        logger.critical("❌ Migración de base de datos falló. Abortando.")
        sys.exit(1)
    
    # Probar conexión a base de datos
    if not test_database_connection():
        logger.critical("❌ Prueba de base de datos falló. Abortando.")
        sys.exit(1)
    
    # Determinar modo de ejecución
    mode = os.getenv('RESERVAS_MODE', 'daemon').lower()
    
    if mode == 'single':
        logger.info("Modo: Procesamiento único")
        if run_single_processing():
            logger.info("✅ Sistema completado exitosamente")
        else:
            logger.error("❌ Procesamiento falló")
            sys.exit(1)
    else:
        logger.info("Modo: Daemon continuo")
        start_reservation_daemon()

if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de migración para añadir la columna hora_cita a la tabla leads
y modificar la columna cita para que sea solo fecha.
Este script está diseñado para ejecutarse durante el despliegue en Railway.
"""

import mysql.connector
import logging
import os
import sys
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)  # Asegurarse de que los logs se muestren en Railway
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def get_db_config():
    """Obtiene la configuración de la base de datos desde las variables de entorno de Railway"""
    # Railway usa MYSQLHOST, MYSQLUSER, etc.
    return {
        'host': os.environ.get('MYSQLHOST', os.environ.get('DB_HOST')),
        'port': int(os.environ.get('MYSQLPORT', os.environ.get('DB_PORT', 3306))),
        'user': os.environ.get('MYSQLUSER', os.environ.get('DB_USER')),
        'password': os.environ.get('MYSQLPASSWORD', os.environ.get('DB_PASSWORD')),
        'database': os.environ.get('MYSQLDATABASE', os.environ.get('DB_DATABASE'))
    }

def run_migration():
    """Ejecuta la migración para añadir la columna hora_cita y modificar la columna cita"""
    connection = None
    try:
        # Obtener configuración de la base de datos
        db_config = get_db_config()
        logger.info(f"Conectando a la base de datos en {db_config['host']}:{db_config['port']} como {db_config['user']}")
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Verificar si la columna hora_cita ya existe
        logger.info("Verificando si la columna hora_cita ya existe...")
        cursor.execute("SHOW COLUMNS FROM leads LIKE 'hora_cita'")
        column_exists = cursor.fetchone()
        
        if not column_exists:
            logger.info("La columna hora_cita no existe. Añadiéndola...")
            
            # Primero, añadir la columna hora_cita
            cursor.execute("""
                ALTER TABLE leads 
                ADD COLUMN hora_cita TIME NULL AFTER cita
            """)
            logger.info("Columna hora_cita añadida correctamente.")
            
            # Verificar el tipo de la columna cita
            cursor.execute("SHOW COLUMNS FROM leads LIKE 'cita'")
            cita_column = cursor.fetchone()
            
            if cita_column and 'datetime' in cita_column[1].lower():
                logger.info("La columna cita es de tipo DATETIME. Extrayendo la hora y guardándola en hora_cita...")
                
                # Extraer la hora de la columna cita existente y guardarla en hora_cita
                cursor.execute("""
                    UPDATE leads 
                    SET hora_cita = TIME(cita) 
                    WHERE cita IS NOT NULL
                """)
                logger.info("Hora extraída y guardada en hora_cita correctamente.")
                
                # Modificar la columna cita para que sea solo fecha
                logger.info("Modificando la columna cita para que sea de tipo DATE...")
                cursor.execute("""
                    ALTER TABLE leads 
                    MODIFY COLUMN cita DATE NULL
                """)
                logger.info("Columna cita modificada a tipo DATE correctamente.")
                
                # Actualizar la columna cita para que contenga solo la fecha
                cursor.execute("""
                    UPDATE leads 
                    SET cita = DATE(cita) 
                    WHERE cita IS NOT NULL
                """)
                logger.info("Datos de fecha actualizados correctamente.")
            else:
                logger.info(f"La columna cita ya es de tipo {cita_column[1] if cita_column else 'desconocido'}. No es necesario modificarla.")
            
            connection.commit()
            logger.info("✅ Migración completada con éxito.")
            return True
        else:
            logger.info("La columna hora_cita ya existe. No se requiere migración.")
            return True
        
    except mysql.connector.Error as err:
        logger.error(f"Error durante la migración: {err}")
        if connection:
            connection.rollback()
        return False
    except Exception as e:
        logger.error(f"Error inesperado durante la migración: {e}", exc_info=True)
        if connection:
            connection.rollback()
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("Conexión cerrada.")

if __name__ == "__main__":
    try:
        logger.info("=== Iniciando migración para añadir hora_cita ===")
        success = run_migration()
        if success:
            logger.info("=== Migración completada con éxito ===")
            sys.exit(0)  # Éxito
        else:
            logger.error("=== La migración falló ===")
            sys.exit(1)  # Error
    except Exception as e:
        logger.error(f"Error catastrófico en la migración: {e}", exc_info=True)
        sys.exit(1)  # Error

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de migración para añadir la columna hora_cita a la tabla leads
y modificar la columna cita para que sea solo fecha.
"""

import mysql.connector
import logging
import os
from dotenv import load_dotenv
from config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_DATABASE
}

def execute_migration():
    """Ejecuta la migración para añadir la columna hora_cita y modificar la columna cita"""
    connection = None
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Verificar si la columna hora_cita ya existe
        cursor.execute("SHOW COLUMNS FROM leads LIKE 'hora_cita'")
        column_exists = cursor.fetchone()
        
        if not column_exists:
            logger.info("Añadiendo columna hora_cita a la tabla leads...")
            
            # Primero, añadir la columna hora_cita
            cursor.execute("""
                ALTER TABLE leads 
                ADD COLUMN hora_cita TIME NULL AFTER cita
            """)
            
            # Extraer la hora de la columna cita existente y guardarla en hora_cita
            cursor.execute("""
                UPDATE leads 
                SET hora_cita = TIME(cita) 
                WHERE cita IS NOT NULL
            """)
            
            # Modificar la columna cita para que sea solo fecha
            cursor.execute("""
                ALTER TABLE leads 
                MODIFY COLUMN cita DATE NULL
            """)
            
            # Actualizar la columna cita para que contenga solo la fecha
            cursor.execute("""
                UPDATE leads 
                SET cita = DATE(cita) 
                WHERE cita IS NOT NULL
            """)
            
            connection.commit()
            logger.info("Migración completada con éxito.")
        else:
            logger.info("La columna hora_cita ya existe. No se requiere migración.")
        
    except mysql.connector.Error as err:
        logger.error(f"Error durante la migración: {err}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("Conexión cerrada.")

if __name__ == "__main__":
    try:
        logger.info("Iniciando migración para añadir hora_cita...")
        execute_migration()
        logger.info("Migración completada.")
    except Exception as e:
        logger.error(f"Error en la migración: {e}")

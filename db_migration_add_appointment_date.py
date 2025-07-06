#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migración para añadir la columna 'fecha_cita' a la tabla 'leads'.
"""

import logging
import mysql.connector
from db import get_connection

# Configuración de logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def anadir_columna_si_no_existe(cursor, tabla, columna, tipo_columna):
    """Añade una columna a una tabla si no existe previamente."""
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{tabla}` LIKE '{columna}'")
        if cursor.fetchone():
            logger.info(f"La columna '{columna}' ya existe en la tabla '{tabla}'. No se realizarán cambios.")
        else:
            logger.info(f"Añadiendo columna '{columna}' a la tabla '{tabla}'...")
            cursor.execute(f"ALTER TABLE `{tabla}` ADD COLUMN `{columna}` {tipo_columna}")
            logger.info(f"Columna '{columna}' añadida con éxito.")
    except mysql.connector.Error as err:
        logger.error(f"Error al intentar añadir la columna '{columna}': {err}")
        raise

def migrar_base_de_datos():
    """Ejecuta el proceso de migración para añadir la columna de fecha de cita."""
    logger.info("Iniciando migración para añadir la columna 'fecha_cita'.")
    connection = None
    try:
        connection = get_connection()
        if connection is None:
            logger.error("No se pudo establecer conexión con la base de datos.")
            return

        cursor = connection.cursor()
        
        anadir_columna_si_no_existe(cursor, 'leads', 'fecha_cita', 'DATETIME NULL')
            
        connection.commit()
        logger.info("Migración para 'fecha_cita' completada con éxito.")

    except mysql.connector.Error as err:
        logger.error(f"Error durante la migración de la base de datos: {err}")
        if connection:
            connection.rollback()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    migrar_base_de_datos()

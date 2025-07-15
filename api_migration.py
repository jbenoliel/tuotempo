#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API temporal para ejecutar la migración de la base de datos.
Este archivo debe eliminarse después de que la migración se haya completado.
"""

from flask import Blueprint, jsonify
import mysql.connector
import logging
import os
import sys
import traceback
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Crear blueprint
migration_api = Blueprint('migration_api', __name__)

def get_db_config():
    """Obtiene la configuración de la base de datos desde las variables de entorno"""
    return {
        'host': os.environ.get('MYSQLHOST', os.environ.get('DB_HOST')),
        'port': int(os.environ.get('MYSQLPORT', os.environ.get('DB_PORT', 3306))),
        'user': os.environ.get('MYSQLUSER', os.environ.get('DB_USER')),
        'password': os.environ.get('MYSQLPASSWORD', os.environ.get('DB_PASSWORD')),
        'database': os.environ.get('MYSQLDATABASE', os.environ.get('DB_DATABASE'))
    }

@migration_api.route('/api/ejecutar_migracion', methods=['GET'])
def ejecutar_migracion():
    """Endpoint para ejecutar la migración de la base de datos"""
    connection = None
    cursor = None
    
    try:
        # Obtener configuración de la base de datos
        db_config = get_db_config()
        logger.info(f"Conectando a la base de datos en {db_config['host']}:{db_config['port']}")
        
        # Conectar a la base de datos con charset explícito
        connection = mysql.connector.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset='utf8mb4',
            use_unicode=True
        )
        cursor = connection.cursor(buffered=True)
        
        # Paso 1: Verificar si la columna hora_cita ya existe
        logger.info("Paso 1: Verificando si la columna hora_cita ya existe...")
        cursor.execute("SHOW COLUMNS FROM leads LIKE 'hora_cita'")
        column_exists = cursor.fetchone()
        
        if not column_exists:
            # Paso 2: Añadir la columna hora_cita
            logger.info("Paso 2: La columna hora_cita no existe. Añadiéndola...")
            cursor.execute("ALTER TABLE leads ADD COLUMN hora_cita TIME NULL AFTER cita")
            logger.info("Columna hora_cita añadida correctamente.")
            
            # Paso 3: Verificar el tipo de la columna cita
            logger.info("Paso 3: Verificando el tipo de la columna cita...")
            cursor.execute("SHOW COLUMNS FROM leads LIKE 'cita'")
            cita_column = cursor.fetchone()
            
            if cita_column and 'datetime' in str(cita_column[1]).lower():
                # Paso 4: Extraer la hora de cita y guardarla en hora_cita
                logger.info("Paso 4: Extrayendo la hora de cita a hora_cita...")
                cursor.execute("UPDATE leads SET hora_cita = TIME(cita) WHERE cita IS NOT NULL")
                logger.info(f"Actualización completada. Filas afectadas: {cursor.rowcount}")
                
                # Paso 5: Modificar la columna cita para que sea solo fecha
                logger.info("Paso 5: Modificando la columna cita a tipo DATE...")
                cursor.execute("ALTER TABLE leads MODIFY COLUMN cita DATE NULL")
                logger.info("Columna cita modificada a tipo DATE correctamente.")
            else:
                logger.info(f"La columna cita ya es de tipo {cita_column[1] if cita_column else 'desconocido'}. No es necesario modificarla.")
            
            # Confirmar cambios
            connection.commit()
            logger.info("Migración completada con éxito.")
            
            return jsonify({
                "success": True,
                "message": "Migración completada con éxito. Se añadió la columna hora_cita y se modificó la columna cita."
            })
        else:
            logger.info("La columna hora_cita ya existe. No se requiere migración.")
            return jsonify({
                "success": True,
                "message": "La columna hora_cita ya existe. No se requiere migración."
            })
        
    except mysql.connector.Error as err:
        error_msg = str(err)
        logger.error(f"Error de MySQL durante la migración: {error_msg}")
        if connection:
            connection.rollback()
        return jsonify({
            "success": False,
            "error": f"Error de base de datos: {error_msg}"
        }), 500
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error inesperado: {error_msg}")
        logger.error(traceback.format_exc())
        if connection:
            connection.rollback()
        return jsonify({
            "success": False,
            "error": f"Error inesperado: {error_msg}"
        }), 500
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.info("Conexión cerrada.")
        except Exception as e:
            logger.error(f"Error al cerrar la conexión: {e}")


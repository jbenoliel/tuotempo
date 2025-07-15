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
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
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
        logger.error(f"Error durante la migración: {err}")
        if connection:
            connection.rollback()
        return jsonify({
            "success": False,
            "error": f"Error de base de datos: {err}"
        }), 500
    except Exception as e:
        logger.error(f"Error inesperado durante la migración: {e}", exc_info=True)
        if connection:
            connection.rollback()
        return jsonify({
            "success": False,
            "error": f"Error inesperado: {e}"
        }), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("Conexión cerrada.")

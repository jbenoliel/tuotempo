#!/usr/bin/env python3
"""
Script para limpiar completamente los datos de Septiembre de Railway
"""

import mysql.connector
import logging
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()

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

def limpiar_septiembre():
    """Limpia completamente los datos de Septiembre"""
    connection = None
    try:
        connection = get_railway_connection()
        cursor = connection.cursor()
        
        # 1. Eliminar leads de Septiembre
        logger.info("Eliminando leads de Septiembre...")
        cursor.execute('DELETE FROM leads WHERE origen_archivo = "Septiembre"')
        leads_eliminados = cursor.rowcount
        logger.info(f"Eliminados {leads_eliminados} leads de Septiembre")
        
        # 2. Marcar archivo como inactivo (sin fecha_desactivacion)
        logger.info("Marcando archivo Septiembre como inactivo...")
        cursor.execute('''
            UPDATE archivos_origen 
            SET activo = FALSE 
            WHERE nombre_archivo = "Septiembre"
        ''')
        archivos_actualizados = cursor.rowcount
        logger.info(f"Archivo Septiembre marcado como inactivo ({archivos_actualizados} registros actualizados)")
        
        # 3. Confirmar cambios
        connection.commit()
        
        logger.info("✅ LIMPIEZA COMPLETADA EXITOSAMENTE")
        logger.info(f"Leads eliminados: {leads_eliminados}")
        logger.info(f"Archivos desactivados: {archivos_actualizados}")
        
        return leads_eliminados
        
    except Exception as e:
        logger.error(f"Error en la limpieza: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    try:
        leads_eliminados = limpiar_septiembre()
        print(f"\n🧹 ¡Limpieza de Septiembre completada!")
        print(f"Leads eliminados: {leads_eliminados}")
    except Exception as e:
        print(f"\n💥 Error en la limpieza: {e}")
        exit(1)
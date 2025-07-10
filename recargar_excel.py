#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para recargar datos de Excel a la base de datos.
Se puede ejecutar directamente o importar y llamar a la función recargar_excel().
También disponible como endpoint web en /recargar-excel
"""

import logging
import mysql.connector
from datetime import datetime
from db import get_connection
from utils import load_excel_data
from init_db import init_database

# Configuración de logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ruta local al archivo Excel de prueba
EXCEL_PATH = r"C:\\Users\\jbeno\\Dropbox\\TEYAME\\Prueba Segurcaixa\\data de prueba callsPearl.xlsx"

def recargar_excel():
    """
    Recarga los datos desde el Excel a la base de datos.
    Retorna: (success, message)
    """
    try:
        # Inicializar base de datos si es necesario
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM leads")
            # Consumir completamente el resultado
            count = cursor.fetchone()[0]
            logger.info(f"La tabla 'leads' existe. Total registros: {count}")
            cursor.close()
            connection.close()
        except mysql.connector.Error as err:
            if err.errno == 1146:  # Table doesn't exist
                logger.info("La tabla 'leads' no existe. Inicializando la base de datos...")
                init_database()
            else:
                logger.error(f"Error al verificar tabla leads: {err}")
                return False, f"Error de base de datos: {err}"
            
        # Conectar a la base de datos (nueva conexión)
        connection = get_connection()
        
        # Cargar datos del Excel
        logger.info(f"Recargando datos desde Excel local: {EXCEL_PATH}")
        stats = load_excel_data(connection, EXCEL_PATH)
        connection.close()
        
        logger.info(f"Resultado carga: {stats}")
        inserted = stats.get('insertados', 0)
        errors = stats.get('errores', 0)
        return True, f"Insertados {inserted}, errores {errors}"
            
    except Exception as e:
        logger.error(f"Error inesperado al recargar Excel: {str(e)}")
        return False, f"Error inesperado: {str(e)}"

# Si se ejecuta directamente, recargar Excel
if __name__ == "__main__":
    success, message = recargar_excel()
    if success:
        print(f"✅ ÉXITO: {message}")
    else:
        print(f"❌ ERROR: {message}")

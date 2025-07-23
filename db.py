"""
Módulo centralizado para la conexión a la base de datos MySQL.
"""
import mysql.connector
from mysql.connector import Error

from config import settings

def get_database_name():
    """Devuelve el nombre de la base de datos desde la configuración."""
    return settings.DB_DATABASE

def get_connection():
    """Obtiene una conexión a MySQL usando la configuración de Settings."""
    cfg = {
        'host': settings.DB_HOST,
        'port': settings.DB_PORT,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'database': settings.DB_DATABASE,
        'ssl_disabled': True,  # Deshabilitar SSL para evitar errores de conexión
        'autocommit': True,
        'charset': 'utf8mb4',
        'use_unicode': True
    }
    try:
        conn = mysql.connector.connect(**cfg)
        return conn
    except Error as e:
        print(f"ERROR conectando a MySQL: {e}")
        # Si falla con SSL, intentar sin SSL
        if 'SSL' in str(e) or '2026' in str(e):
            try:
                print("Intentando conexión sin SSL...")
                cfg_no_ssl = cfg.copy()
                cfg_no_ssl['ssl_disabled'] = True
                conn = mysql.connector.connect(**cfg_no_ssl)
                return conn
            except Error as e2:
                print(f"ERROR conectando sin SSL: {e2}")
        return None
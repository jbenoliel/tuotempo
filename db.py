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
    # Ensure all config values are strings and not None
    host = str(settings.DB_HOST) if settings.DB_HOST is not None else 'localhost'
    port = int(settings.DB_PORT) if settings.DB_PORT is not None else 3306
    user = str(settings.DB_USER) if settings.DB_USER is not None else 'root'
    password = str(settings.DB_PASSWORD) if settings.DB_PASSWORD is not None else ''
    database = str(settings.DB_DATABASE) if settings.DB_DATABASE is not None else 'Segurcaixa'
    
    cfg = {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database,
        'ssl_disabled': True,
        'autocommit': True,
        'charset': 'utf8',  # Changed from utf8mb4 to avoid character set issues
        'use_unicode': False,  # Disabled to avoid None issues
        'sql_mode': ''
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
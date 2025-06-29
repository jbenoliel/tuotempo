"""
Módulo centralizado para la conexión a la base de datos MySQL.
"""
import mysql.connector
from mysql.connector import Error

from config import settings

def get_connection():
    """Obtiene una conexión a MySQL usando la configuración de Settings."""
    cfg = {
        'host': settings.DB_HOST,
        'port': settings.DB_PORT,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'database': settings.DB_DATABASE,
    }
    try:
        conn = mysql.connector.connect(**cfg)
        return conn
    except Error as e:
        # Logging mínimo, el llamante puede manejar el error
        print(f"ERROR conectando a MySQL: {e}")
        return None
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Carga variables de entorno desde .env en desarrollo local
load_dotenv()

class Settings:
    """Configuración de la aplicación y base de datos"""
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia_este_valor_en_produccion")

    # Base de datos MySQL - Lógica robusta para Railway y local
    MYSQL_URL = os.environ.get("MYSQL_URL")

    if MYSQL_URL:
        # Si estamos en Railway (o un entorno con URL de conexión)
        url = urlparse(MYSQL_URL)
        DB_HOST = url.hostname
        DB_PORT = url.port or 3306
        DB_USER = url.username
        DB_PASSWORD = url.password
        DB_DATABASE = url.path[1:] if url.path else None # Eliminar la barra inicial y manejar path vacío
    else:
        # Si estamos en local, usar las variables individuales
        DB_HOST = os.environ.get("MYSQL_HOST", os.environ.get("MYSQLHOST", "localhost"))
        DB_PORT = int(os.environ.get("MYSQL_PORT", os.environ.get("MYSQLPORT", 3306)))
        DB_USER = os.environ.get("MYSQL_USER", os.environ.get("MYSQLUSER", "root"))
        DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", os.environ.get("MYSQLPASSWORD", ""))
        DB_DATABASE = os.environ.get("MYSQL_DATABASE", os.environ.get("MYSQLDATABASE", "Segurcaixa"))

settings = Settings()
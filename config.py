import os
from dotenv import load_dotenv

# Carga variables de entorno desde .env en desarrollo local
load_dotenv()

class Settings:
    """Configuración de la aplicación y base de datos"""
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia_este_valor_en_produccion")

    # Base de datos MySQL
    DB_HOST = os.environ.get("MYSQL_HOST", os.environ.get("MYSQLHOST", "localhost"))
    DB_PORT = int(os.environ.get("MYSQL_PORT", os.environ.get("MYSQLPORT", 3306)))
    DB_USER = os.environ.get("MYSQL_USER", os.environ.get("MYSQLUSER", "root"))
    DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", os.environ.get("MYSQLPASSWORD", ""))
    DB_DATABASE = os.environ.get("MYSQL_DATABASE", os.environ.get("MYSQLDATABASE", "Segurcaixa"))

settings = Settings()
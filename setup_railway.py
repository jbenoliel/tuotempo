import os
import pymysql
import bcrypt
from dotenv import load_dotenv
import logging

# Configurar logging para ver la salida en los logs de Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_admin_user():
    """
    Asegura que el usuario 'admin' exista con la contraseña 'admin' y los permisos correctos.
    Este script está diseñado para ejecutarse en el arranque del despliegue en Railway.
    """
    load_dotenv()

    db_host = os.getenv('MYSQL_HOST')
    db_user = os.getenv('MYSQL_USER')
    db_password = os.getenv('MYSQL_PASSWORD')
    db_name = os.getenv('MYSQL_DATABASE')

    if not all([db_host, db_user, db_password, db_name]):
        logging.error("Las variables de entorno de la base de datos no están configuradas. Abortando.")
        return

    try:
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        logging.info("Conexión exitosa a la base de datos.")
    except pymysql.MySQLError as e:
        logging.error(f"Error al conectar a MySQL: {e}")
        return

    try:
        with conn.cursor() as cursor:
            # Buscar si el usuario admin existe
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", ('admin',))
            user = cursor.fetchone()

            admin_password = 'admin'
            password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')

            if user:
                # Si existe, se actualiza para asegurar los permisos y la contraseña
                logging.info("Usuario 'admin' encontrado. Actualizando contraseña y permisos.")
                cursor.execute(
                    """
                    UPDATE usuarios 
                    SET password_hash = %s, is_admin = 1, is_active = 1, email_verified = 1
                    WHERE id = %s
                    """,
                    (password_hash, user['id'])
                )
                logging.info("Usuario 'admin' actualizado correctamente.")
            else:
                # Si no existe, se crea
                logging.info("Usuario 'admin' no encontrado. Creando nuevo usuario 'admin'.")
                cursor.execute(
                    """
                    INSERT INTO usuarios (username, email, password_hash, is_admin, is_active, email_verified)
                    VALUES (%s, %s, %s, 1, 1, 1)
                    """,
                    ('admin', admin_email, password_hash)
                )
                logging.info("Usuario 'admin' creado correctamente.")
            
            conn.commit()

    except pymysql.MySQLError as e:
        logging.error(f"Ocurrió un error en la operación de base de datos: {e}")
    finally:
        conn.close()
        logging.info("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    logging.info("Iniciando script de configuración de usuario admin para Railway...")
    setup_admin_user()
    logging.info("Script de configuración de usuario admin finalizado.")

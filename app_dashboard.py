import os
import logging


from flask import Flask
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar Bcrypt como una variable global para ser usada en la factory
bcrypt = Bcrypt()

def create_app(config_class='config.settings'):
    """Factory para crear y configurar la aplicación Flask."""
    app = Flask(__name__)
    
    # 1. Cargar configuración
    app.config.from_object(config_class)
    
    # 2. Configurar el logging
    logging.basicConfig(level=app.config.get('LOG_LEVEL', 'INFO'),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 3. Inicializar extensiones
    bcrypt.init_app(app)
    
    # Adjuntar bcrypt a la app para que esté disponible en los blueprints
    # aunque no es la forma más limpia, es una solución rápida.
    # Una mejor forma sería usar el contexto de la aplicación `g`.
    app.bcrypt = bcrypt

    # 4. Registrar Blueprints
    with app.app_context():
        from blueprints import bp as main_blueprint
        app.register_blueprint(main_blueprint)

    # 5. Definir un comando CLI para crear un usuario (opcional pero útil)
    @app.cli.command("create-user")
    def create_user():
        """Crea un usuario administrador inicial."""
        from db import get_connection
        from getpass import getpass

        username = input("Username: ")
        password = getpass("Password: ")
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, is_admin) VALUES (%s, %s, %s)",
                (username, password_hash, True)
            )
            conn.commit()
            print(f"Usuario '{username}' creado exitosamente.")
        except Exception as e:
            print(f"Error al crear el usuario: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    return app

# Crear la aplicación para que Gunicorn la detecte
app = create_app()

if __name__ == '__main__':
    # Crear la aplicación usando la factory
    app = create_app()
    # El modo debug y el puerto se pueden controlar desde el archivo de configuración
    app.run(debug=app.config.get('DEBUG', True), 
            port=app.config.get('PORT', 5000),
            host=app.config.get('HOST', '0.0.0.0'))

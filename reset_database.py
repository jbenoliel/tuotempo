import os
import sys
from db import get_connection
from dotenv import load_dotenv

# Cargar variables de entorno desde .env para ejecución local
load_dotenv()

def reset_database():
    """
    Ejecuta el script schema.sql para borrar y recrear la base de datos.
    ADVERTENCIA: Esta es una operación destructiva.
    """
    
    # --- Advertencia de Seguridad ---
    print("="*60)
    print("ATENCIÓN: ESTE SCRIPT BORRARÁ TODAS LAS TABLAS Y DATOS")
    print("DE LA BASE DE DATOS Y LAS RECREARÁ DESDE CERO.")
    print("Esta acción es IRREVERSIBLE.")
    print("="*60)
    
    confirm = input("Escribe 'SI' en mayúsculas para confirmar y continuar: ")
    
    if confirm != 'SI':
        print("\nOperación cancelada por el usuario.")
        sys.exit(0)

    print("\nProcediendo con el reseteo de la base de datos...")

    try:
        # Construir la ruta al archivo schema.sql
        script_dir = os.path.dirname(__file__)
        schema_path = os.path.join(script_dir, 'schema.sql')

        if not os.path.exists(schema_path):
            print(f"Error: No se encuentra el archivo 'schema.sql' en la ruta: {schema_path}")
            sys.exit(1)

        # Leer el contenido del script SQL
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

    except Exception as e:
        print(f"Error leyendo el archivo schema.sql: {e}")
        sys.exit(1)

    connection = None
    try:
        # Obtener conexión a la base de datos
        connection = get_connection()
        if not connection:
            print("Error: No se pudo establecer conexión con la base de datos.")
            sys.exit(1)
            
        cursor = connection.cursor()

        # El argumento 'multi=True' puede fallar. Un método más robusto es dividir
        # el script en sentencias individuales y ejecutarlas una por una.
        print("Ejecutando script SQL, sentencia por sentencia...")

        # Dividimos el script por ';' que es el delimitador en nuestro schema.sql
        sql_commands = [command.strip() for command in sql_script.split(';') if command.strip()]

        for command in sql_commands:
            print(f"  - Ejecutando: {command[:70]}...")
            cursor.execute(command)

        connection.commit()
        print("\n¡Éxito! La base de datos ha sido reseteada correctamente.")
        print("Se ha creado el usuario 'admin' con la contraseña 'admin'.")

    except Exception as e:
        print(f"\nError durante la ejecución del script SQL: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    reset_database()

import os
import subprocess
import json

def get_railway_connection_url():
    """Obtener la URL de conexión a la base de datos MySQL en Railway"""
    try:
        # Ejecutar el comando railway variables para obtener las variables de entorno
        result = subprocess.run(['railway', 'variables', '--service', 'MySQL', '--json'], 
                               capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error al ejecutar railway variables: {result.stderr}")
            return None
        
        # Parsear el resultado como JSON
        try:
            variables = json.loads(result.stdout)
            
            # Buscar la variable DATABASE_URL o construirla a partir de componentes
            if 'DATABASE_URL' in variables:
                return variables['DATABASE_URL']
            
            # Si no hay DATABASE_URL, intentar construirla a partir de componentes
            host = variables.get('MYSQLHOST', '')
            port = variables.get('MYSQLPORT', '3306')
            user = variables.get('MYSQLUSER', 'root')
            password = variables.get('MYSQLPASSWORD', '')
            database = variables.get('MYSQLDATABASE', 'railway')
            
            # Construir la URL de conexión
            connection_url = f"mysql://{user}:{password}@{host}:{port}/{database}"
            return connection_url
        except json.JSONDecodeError:
            print(f"Error al parsear la salida como JSON: {result.stdout}")
            return None
    except Exception as e:
        print(f"Error al obtener la URL de conexión: {e}")
        return None

if __name__ == "__main__":
    connection_url = get_railway_connection_url()
    if connection_url:
        # Ocultar la contraseña para mostrarla
        parts = connection_url.split('@')
        if len(parts) > 1:
            user_pass = parts[0].split('://')
            if len(user_pass) > 1:
                protocol = user_pass[0]
                credentials = user_pass[1].split(':')
                if len(credentials) > 1:
                    user = credentials[0]
                    masked_url = f"{protocol}://{user}:****@{parts[1]}"
                    print(f"URL de conexión a Railway (contraseña oculta): {masked_url}")
                else:
                    print(f"URL de conexión a Railway: {connection_url}")
            else:
                print(f"URL de conexión a Railway: {connection_url}")
        else:
            print(f"URL de conexión a Railway: {connection_url}")
    else:
        print("No se pudo obtener la URL de conexión a Railway")

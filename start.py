import os
import sys
import subprocess
import time

# Obtener el nombre del servicio de la variable de entorno que proporciona Railway.
service_name = os.environ.get('RAILWAY_SERVICE_NAME')

print("--- Script Despachador de Servicios ---")
print(f"Tiempo de inicio: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Directorio actual: {os.getcwd()}")
print(f"Archivos disponibles: {os.listdir('.')}")

if not service_name:
    print("Error: La variable de entorno RAILWAY_SERVICE_NAME no está definida.")
    print("Este script está diseñado para correr en Railway.")
    sys.exit(1)

print(f"Servicio detectado: {service_name}")

# Mapeo de nombres de servicio a los comandos de inicio correctos.
# ¡IMPORTANTE! Los nombres aquí deben coincidir con los de tu panel de Railway.
commands = {
    'web': 'gunicorn app_dashboard:app',
    'dashboard': 'gunicorn app_dashboard:app',
    'actualizarllamadas': 'gunicorn api_resultado_llamada:app',
    'tuotempo apis': 'gunicorn api_tuotempo:app',
    'tuotempo-apis': 'gunicorn api_tuotempo:app',
    'tuotempo-apis-production': 'gunicorn api_tuotempo:app',
}

# MANEJO ESPECIAL para el servicio de APIs - match prioritario y exacto
if 'tuotempo-apis-production' == service_name:
    print("¡COINCIDENCIA EXACTA para tuotempo-apis-production!")
    command_to_run = 'gunicorn api_tuotempo:app'
else:
    # Buscar el comando correspondiente al servicio actual para otros servicios
    # Convertimos el nombre del servicio a minúsculas para una comparación robusta.
    print(f"Buscando coincidencia para: '{service_name}'")
    service_name_lower = service_name.lower()
    command_to_run = None
    for key, command in commands.items():
        print(f"Comprobando si '{key}' coincide con '{service_name_lower}'")
        # Las claves en nuestro diccionario ya están en minúsculas.
        if key in service_name_lower:
            command_to_run = command
            print(f"¡Coincidencia encontrada! Usando comando: {command}")
            break

if command_to_run:
    print(f"Ejecutando comando: '{command_to_run}'")
    # Usamos subprocess.run para lanzar el proceso. En el entorno de Railway (Linux),
    # execvpe sería ideal, pero esto es más compatible y robusto.
    try:
        subprocess.run(command_to_run, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando: {e}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Error: El comando '{command_to_run.split()[0]}' no se encontró. ¿Está gunicorn instalado?")
        sys.exit(1)
else:
    print(f"Error: No se encontró un comando de inicio para el servicio '{service_name}'.")
    print("Verifica los nombres de servicio en 'start.py' y en tu proyecto de Railway.")
    sys.exit(1)

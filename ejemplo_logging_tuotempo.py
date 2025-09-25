"""
Ejemplo de uso del sistema de logging de APIs de tuotempo.

Este archivo muestra cómo funciona el logging automático de las llamadas
a las APIs de tuotempo.
"""

import os
from dotenv import load_dotenv
from tuotempo import Tuotempo
from tuotempo_api import TuoTempoAPI
import json

# Load environment variables
load_dotenv()

def ejemplo_logging_basico():
    """
    Ejemplo básico mostrando el logging automático.
    """
    print("=== Ejemplo de Logging de APIs de tuotempo ===")

    # Inicializar cliente de tuotempo
    api_key = "24b98d8d41b970d38362b52bd3505c04"  # PRO environment
    instance_id = "tt_portal_adeslas"

    tuotempo = Tuotempo(api_key, "secret", instance_id)

    # Ejemplo 1: Obtener slots disponibles
    print("\n1. Obteniendo slots disponibles...")
    try:
        slots = tuotempo.get_available_slots(
            locations_lid=["44kowswy"],
            start_date="25-12-2024",
            days=7
        )
        print(f"Slots obtenidos: {len(slots.get('availabilities', []))} disponibles")
    except Exception as e:
        print(f"Error al obtener slots: {e}")

    # Ejemplo 2: Crear una reserva de prueba
    print("\n2. Simulando creación de reserva...")
    user_info = {
        "name": "Juan",
        "surname": "Pérez",
        "birth_date": "1990-01-01",
        "mobile_phone": "123456789"
    }

    availability = {
        "start_date": "25-12-2024",
        "startTime": "10:00",
        "endTime": "10:30",
        "resourceid": "test-resource",
        "activityid": "sc159232371eb9c1"
    }

    try:
        reservation = tuotempo.create_reservation(user_info, availability)
        print(f"Reserva creada: {reservation.get('result', 'ERROR')}")
    except Exception as e:
        print(f"Error al crear reserva: {e}")

def ejemplo_cliente_directo():
    """
    Ejemplo usando directamente TuoTempoAPI.
    """
    print("\n=== Ejemplo con TuoTempoAPI directo ===")

    api_key = "24b98d8d41b970d38362b52bd3505c04"  # PRO environment
    client = TuoTempoAPI(
        instance_id="tt_portal_adeslas",
        api_key=api_key,
        environment="PRO"
    )

    # Ejemplo 1: Obtener centros
    print("\n1. Obteniendo centros...")
    try:
        centers = client.get_centers()
        print(f"Centros obtenidos: {len(centers.get('areas', []))} centros")
    except Exception as e:
        print(f"Error al obtener centros: {e}")

    # Ejemplo 2: Registrar usuario
    print("\n2. Registrando usuario de prueba...")
    try:
        user_registration = client.register_non_insured_user(
            fname="María",
            lname="González",
            birthday="1985-05-15",
            phone="987654321"
        )
        print(f"Usuario registrado: {user_registration.get('result', 'ERROR')}")
    except Exception as e:
        print(f"Error al registrar usuario: {e}")

def mostrar_logs():
    """
    Muestra cómo revisar los logs generados.
    """
    print("\n=== Revisando logs generados ===")

    log_file = "logs/tuotempo_api_calls.log"

    if os.path.exists(log_file):
        print(f"\nLeyendo últimas líneas del archivo de log: {log_file}")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Mostrar las últimas 5 líneas
            for line in lines[-5:]:
                try:
                    log_entry = json.loads(line.split(' | ', 1)[1])
                    print(f"- {log_entry['timestamp']}: {log_entry.get('function', log_entry.get('method'))} -> {log_entry.get('success', 'N/A')}")
                except:
                    print(f"- {line.strip()}")
    else:
        print(f"Archivo de log no encontrado: {log_file}")
        print("Ejecuta algunas llamadas a las APIs para generar logs.")

if __name__ == "__main__":
    # Ejecutar ejemplos
    ejemplo_logging_basico()
    ejemplo_cliente_directo()

    # Mostrar logs
    mostrar_logs()

    print("\n=== Información importante ===")
    print("Todos los logs de las APIs de tuotempo se guardan en: logs/tuotempo_api_calls.log")
    print("Cada entrada contiene:")
    print("- timestamp: Fecha y hora de la llamada")
    print("- method/function: Método HTTP o función llamada")
    print("- params/args: Parámetros enviados")
    print("- response/result: Respuesta recibida")
    print("- success: Si la llamada fue exitosa")
    print("- error: Error si ocurrió alguno")
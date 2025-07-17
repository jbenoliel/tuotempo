import requests
import os

# Lista de URLs de los servicios a verificar
# La URL base se puede obtener de las variables de entorno de Railway si está disponible
BASE_URL = os.environ.get("RAILWAY_STATIC_URL", "tuotempo-apis-production.up.railway.app")

SERVICES_TO_CHECK = {
    "API Principal": f"https://{BASE_URL}",
    "API de Resultados": f"https://{BASE_URL}/api/actualizar_resultado",
    # Añade aquí otros servicios que quieras monitorizar
    # "Otro Servicio": f"https://{BASE_URL}/otro/endpoint",
}

def check_service_status():
    """Verifica el estado de los servicios definidos en SERVICES_TO_CHECK."""
    print("Iniciando verificación de estado de los servicios en Railway...\n")
    all_ok = True

    for service_name, url in SERVICES_TO_CHECK.items():
        try:
            # Para el endpoint de actualizar_resultado, usamos POST como método
            if "actualizar_resultado" in url:
                # Hacemos una llamada POST con un cuerpo de prueba para verificar el endpoint
                test_payload = {
                    "phone": "+34600000000",  # Número de teléfono de prueba
                    "result": "Prueba de Conexión", # Resultado de prueba
                    "lead_id": 0 # ID de lead de prueba
                }
                response = requests.post(url, json=test_payload, timeout=10)
            else:
                response = requests.get(url, timeout=10)

            if response.status_code == 200:
                print(f"\033[92m✔ {service_name}: OK ({response.status_code})\033[0m")
            elif response.status_code == 405: # Method Not Allowed
                 print(f"\033[92m✔ {service_name}: Endpoint existe pero método incorrecto ({response.status_code}) - ¡Buena señal!\033[0m")
            else:
                print(f"\033[91m✗ {service_name}: ERROR ({response.status_code})\033[0m")
                all_ok = False
        except requests.exceptions.RequestException as e:
            print(f"\033[91m✗ {service_name}: ERROR DE CONEXIÓN - {e}\033[0m")
            all_ok = False

    print("\nVerificación completada.")
    if all_ok:
        print("\033[92mTodos los servicios parecen estar operativos.\033[0m")
    else:
        print("\033[91mAlgunos servicios presentan problemas.\033[0m")

if __name__ == "__main__":
    check_service_status()

#!/usr/bin/env python3
"""
Prueba la API /start para verificar que ya no hace timeout
"""

import requests
import json
import time

def test_start_api():
    """Prueba el endpoint /start de forma manual"""

    print("=== PRUEBA API /start ===")
    print()

    # URL de Railway
    base_url = "https://web-production-b743.up.railway.app/api/calls"

    # Configuracion de prueba
    test_config = {
        "max_concurrent": 1,
        "selected_leads": [4, 7, 8],  # IDs de ejemplo que sabemos que existen
        "override_phone": "+34600000000"  # Telefono de prueba
    }

    print(f"URL: {base_url}/start")
    print(f"Config: {json.dumps(test_config, indent=2)}")
    print()

    start_time = time.time()

    try:
        print("Enviando peticion...")
        response = requests.post(
            f"{base_url}/start",
            json=test_config,
            timeout=30  # Timeout de 30 segundos
        )

        elapsed_time = time.time() - start_time
        print(f"Tiempo de respuesta: {elapsed_time:.2f} segundos")
        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            print("RESPUESTA EXITOSA:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if data.get('success'):
                print()
                print("[OK] API respondio correctamente!")
                print("El sistema deberia estar procesando en background")

                # Esperar un poco y verificar status
                print("\nEsperando 5 segundos...")
                time.sleep(5)

                print("Verificando status...")
                status_response = requests.get(f"{base_url}/status", timeout=10)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print("STATUS:")
                    print(json.dumps(status_data, indent=2, ensure_ascii=False))

            else:
                print("[ERROR] API respondio pero con success=false")

        else:
            print(f"ERROR HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")

    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        print(f"[TIMEOUT] La peticion tardo mas de 30 segundos ({elapsed_time:.2f}s)")
        print("El problema del timeout NO esta resuelto")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexion: {e}")

if __name__ == "__main__":
    test_start_api()
    print()
    print("=" * 50)
    print("Si la respuesta llego en menos de 5 segundos,")
    print("el problema del timeout esta RESUELTO")
#!/usr/bin/env python3
"""
Prueba la respuesta exacta de la API que esta recibiendo el call-manager
para entender por que JavaScript interpreta que no hay leads
"""

import requests
import json
from urllib.parse import urlencode

def test_count_api_response():
    """Simula exactamente la llamada que hace el JavaScript"""

    print("=== SIMULACION LLAMADA JAVASCRIPT ===")
    print()

    # URL base - ajustar según tu entorno
    # Si el call-manager esta corriendo localmente pero apunta a Railway:
    base_url = "https://web-production-b743.up.railway.app/api/calls"  # URL de Railway
    # O si es local: base_url = "http://localhost:8080/api/calls"

    # Parametros exactos como los envia JavaScript
    params = {
        'status_field': 'status_level_1',
        'status_value': 'Volver a llamar',
        'archivo_origen': 'SEGURCAIXA_JULIO'  # JavaScript puede enviar como string, no array
    }

    print(f"URL: {base_url}/leads/count-by-status")
    print(f"Parametros: {params}")
    print()

    try:
        # Llamada GET exacta
        response = requests.get(
            f"{base_url}/leads/count-by-status",
            params=params,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()

        if response.status_code == 200:
            try:
                data = response.json()
                print("RESPUESTA JSON COMPLETA:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print()

                # Analizar los campos que JavaScript verifica
                success = data.get('success', False)
                total_count = data.get('total_count', 0)
                selected_count = data.get('selected_count', 0)
                not_selected_count = data.get('not_selected_count', 0)

                print("ANALISIS PARA JAVASCRIPT:")
                print(f"  success: {success}")
                print(f"  total_count: {total_count}")
                print(f"  selected_count: {selected_count}")
                print(f"  not_selected_count: {not_selected_count}")
                print()

                # Diagnostico del problema JavaScript
                if not success:
                    print("[PROBLEMA] success = false")
                elif total_count == 0:
                    print("[PROBLEMA] total_count = 0")
                elif not_selected_count == 0:
                    print("[PROBLEMA] not_selected_count = 0 (JavaScript interpreta como 'no leads disponibles')")
                else:
                    print(f"[OK] JavaScript deberia ver {not_selected_count} leads disponibles")

            except json.JSONDecodeError as e:
                print(f"ERROR: Respuesta no es JSON válido: {e}")
                print(f"Contenido: {response.text[:200]}...")

        else:
            print(f"ERROR HTTP {response.status_code}")
            print(f"Contenido: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"ERROR de conexion: {e}")
        print()
        print("POSIBLES CAUSAS:")
        print("- URL incorrecta")
        print("- Servidor no disponible")
        print("- Problema de conectividad")

def test_with_array_parameter():
    """Prueba con parametro como array (como deberia ser)"""

    print()
    print("=== PRUEBA CON PARAMETRO COMO ARRAY ===")
    print()

    base_url = "https://web-production-b743.up.railway.app/api/calls"

    # Usar requests para enviar archivo_origen como array
    params = {
        'status_field': 'status_level_1',
        'status_value': 'Volver a llamar'
    }

    # Añadir archivo_origen como lista
    url = f"{base_url}/leads/count-by-status?" + urlencode(params) + "&archivo_origen=SEGURCAIXA_JULIO"

    print(f"URL completa: {url}")

    try:
        response = requests.get(url, timeout=10)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("Respuesta:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            not_selected = data.get('not_selected_count', 0)
            print(f"\nLeads disponibles: {not_selected}")
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("PRUEBA DE RESPUESTA API PARA CALL-MANAGER")
    print("=" * 60)

    test_count_api_response()
    test_with_array_parameter()

    print()
    print("=" * 60)
    print("Si la API devuelve not_selected_count > 0 pero JavaScript")
    print("dice 'no leads', el problema esta en la logica de JavaScript")
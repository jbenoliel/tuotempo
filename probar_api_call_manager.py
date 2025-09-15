#!/usr/bin/env python3
"""
Prueba directa de la API del call-manager para ver exactamente que ocurre
"""

import requests
import json

# URL base de la API (ajustar segun tu configuracion)
BASE_URL = "http://localhost:8080/api/calls"  # Cambiar si es diferente

def test_count_api():
    """Prueba el endpoint de conteo"""

    print("=== PRUEBA API: COUNT-BY-STATUS ===")
    print()

    # Parametros exactos como los usa el call-manager
    params = {
        'status_field': 'status_level_1',
        'status_value': 'Volver a llamar',
        'archivo_origen': ['SEGURCAIXA_JULIO']
    }

    print(f"Llamando: {BASE_URL}/leads/count-by-status")
    print(f"Parametros: {params}")
    print()

    try:
        response = requests.get(f"{BASE_URL}/leads/count-by-status", params=params)

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"Respuesta JSON: {json.dumps(data, indent=2)}")

            total = data.get('total_count', 0)
            selected = data.get('selected_count', 0)
            available = data.get('not_selected_count', 0)

            print()
            print("RESULTADO:")
            print(f"  Total que cumple criterios: {total}")
            print(f"  Ya seleccionados: {selected}")
            print(f"  Disponibles: {available}")

            if available == 0:
                print("  [PROBLEMA] API reporta 0 disponibles!")
            else:
                print(f"  [OK] API reporta {available} disponibles")

        else:
            print(f"Error HTTP: {response.status_code}")
            print(f"Respuesta: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error de conexion: {e}")
        print()
        print("NOTA: Asegurate de que el servidor este corriendo en el puerto 8080")
        print("Si usas un puerto diferente, actualiza BASE_URL en este script")

def test_select_api():
    """Prueba el endpoint de seleccion"""

    print()
    print("=== PRUEBA API: SELECT-BY-STATUS ===")
    print()

    # Datos exactos como los envia el call-manager
    data = {
        'status_field': 'status_level_1',
        'status_value': 'Volver a llamar',
        'archivo_origen': ['SEGURCAIXA_JULIO'],
        'selected': True
    }

    print(f"Llamando: {BASE_URL}/leads/select-by-status")
    print(f"Datos JSON: {json.dumps(data, indent=2)}")
    print()

    try:
        response = requests.post(
            f"{BASE_URL}/leads/select-by-status",
            json=data,
            headers={'Content-Type': 'application/json'}
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Respuesta JSON: {json.dumps(result, indent=2)}")

            selected_count = result.get('selected_count', 0)
            message = result.get('message', '')

            print()
            print("RESULTADO:")
            print(f"  Leads seleccionados: {selected_count}")
            print(f"  Mensaje: {message}")

            if selected_count == 0:
                print("  [PROBLEMA] API selecciono 0 leads!")
            else:
                print(f"  [OK] API selecciono {selected_count} leads")

        else:
            print(f"Error HTTP: {response.status_code}")
            print(f"Respuesta: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error de conexion: {e}")

if __name__ == "__main__":
    print("PRUEBA DIRECTA DE API CALL-MANAGER")
    print("=" * 50)

    test_count_api()

    # Solo probar seleccion si el conteo funciona
    respuesta = input("\n¿Quieres probar tambien la seleccion? (y/n): ").strip().lower()
    if respuesta == 'y':
        test_select_api()

    print()
    print("=" * 50)
    print("PRUEBA COMPLETADA")
#!/usr/bin/env python3
"""
Test de llamada a API de Railway
"""
import requests
import json

def test_api_call():
    """Probar llamada a la API de Railway"""
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Payload de prueba
    test_payload = {
        "telefono": "999999999",  # Teléfono de prueba
        "volverALlamar": True,
        "razonvueltaallamar": "Test desde local - verificar Railway",
        "codigoVolverLlamar": "interrupcion"
    }
    
    headers = {'Content-Type': 'application/json'}
    
    print("=== TEST DE API RAILWAY ===")
    print(f"URL: {api_url}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print()
    
    try:
        response = requests.post(api_url, json=test_payload, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("API CALL EXITOSA")
            print(f"Message: {result.get('message', 'No message')}")
        else:
            print("API CALL FALLO (esperado con telefono de prueba)")
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR DE CONEXION: {e}")
    except Exception as e:
        print(f"ERROR GENERAL: {e}")

if __name__ == "__main__":
    test_api_call()
#!/usr/bin/env python3
"""
Test específico para SILVIA EUGENIA que está fallando
"""
import requests
import json

def test_silvia_eugenia():
    """Test específico para el caso problemático"""
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Payload simplificado para SILVIA EUGENIA
    payload = {
        "telefono": "637284071",
        "noInteresado": True,
        "razonNoInteres": "Cliente no interesado",  # Texto simple, sin arrays
        "codigoNoInteres": "otros"
    }
    
    headers = {'Content-Type': 'application/json'}
    
    print("=== TEST SILVIA EUGENIA MENDOZA ===")
    print(f"Telefono: 637284071")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Registro corregido")
            print("Expected: status_level_1 = 'No Interesado', status_level_2 = 'No da motivos'")
        elif response.status_code == 404:
            print("Teléfono no encontrado en BD")
        else:
            print(f"ERROR: Status {response.status_code}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_silvia_eugenia()
#!/usr/bin/env python3
"""
Test simple de subestados
"""
import requests
import json

def test_simple():
    """Test simple sin emojis"""
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Test con código interrupcion
    payload = {
        "telefono": "615029152",  
        "volverALlamar": True,
        "razonvueltaallamar": "Cliente no disponible - TEST",
        "codigoVolverLlamar": "interrupcion"
    }
    
    headers = {'Content-Type': 'application/json'}
    
    print("TEST: Volver a llamar con codigo interrupcion")
    print("Esperado: status_level_2 = 'no disponible cliente'")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: API actualizada correctamente")
            print("Verifica en el dashboard el subestado")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_simple()
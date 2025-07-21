#!/usr/bin/env python3
"""
Test de la corrección de subestados
"""
import requests
import json
import time

def test_subestados_fix():
    """Probar que los subestados ahora se mapean correctamente"""
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Casos de test
    test_cases = [
        {
            "name": "Volver a llamar con código interrupcion",
            "payload": {
                "telefono": "615029152",  # PAOLA MONTERO ROLDAN
                "volverALlamar": True,
                "razonvueltaallamar": "Cliente no disponible",
                "codigoVolverLlamar": "interrupcion"
            },
            "expected_level_2": "no disponible cliente"
        },
        {
            "name": "Volver a llamar con código buzón",
            "payload": {
                "telefono": "639328670",  # FRANCISCA JIMENEZ
                "volverALlamar": True,
                "razonvueltaallamar": "Buzón de voz",
                "codigoVolverLlamar": "buzon"
            },
            "expected_level_2": "buzón"
        },
        {
            "name": "No interesado con código otros",
            "payload": {
                "telefono": "630474787",  # MARIA CONCEPCIO
                "noInteresado": True,
                "razonNoInteres": "Cliente no interesado",
                "codigoNoInteres": "otros"
            },
            "expected_level_2": "No da motivos"
        }
    ]
    
    headers = {'Content-Type': 'application/json'}
    
    print("=== TEST DE CORRECCION DE SUBESTADOS ===")
    print("Esperando que Railway complete el deploy...")
    time.sleep(10)  # Esperar deploy
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'-'*60}")
        print(f"TEST {i}: {test_case['name']}")
        print(f"Expected status_level_2: {test_case['expected_level_2']}")
        print(f"Payload: {json.dumps(test_case['payload'], indent=2)}")
        print(f"{'-'*60}")
        
        try:
            response = requests.post(api_url, json=test_case['payload'], headers=headers, timeout=30)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ API CALL EXITOSA")
            else:
                print("❌ API CALL FALLO")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        if i < len(test_cases):
            time.sleep(2)  # Pausa entre tests
    
    print(f"\n{'='*60}")
    print("TESTS COMPLETADOS")
    print("Verifica ahora en el dashboard que los subestados aparecen correctamente.")
    print("Debería mostrar:")
    print("- 615029152: Volver a llamar -> no disponible cliente")
    print("- 639328670: Volver a llamar -> buzón") 
    print("- 630474787: No Interesado -> No da motivos")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_subestados_fix()
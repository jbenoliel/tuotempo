#!/usr/bin/env python3
"""
Debug para entender por qué faltan subestados
"""
import requests
import json

def test_api_response():
    """Test para ver exactamente qué está pasando con la API"""
    
    # Test con un teléfono conocido
    telefono_test = "630474787"  # MARIA CONCEPCIO
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    print("=== DEBUG DE SUBESTADOS ===")
    print(f"Testing con teléfono: {telefono_test}")
    print()
    
    # Test 1: Volver a llamar
    print("TEST 1: Forzar 'Volver a llamar' con subestado")
    payload1 = {
        "telefono": telefono_test,
        "volverALlamar": True,
        "razonvueltaallamar": "Cliente no disponible - TEST",
        "codigoVolverLlamar": "interrupcion"
    }
    
    print(f"Payload: {json.dumps(payload1, indent=2)}")
    
    try:
        response = requests.post(api_url, json=payload1, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        if response.status_code == 200:
            print("ESPERADO en BD:")
            print("- status_level_1: 'Volver a llamar'")
            print("- status_level_2: 'no disponible cliente'")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("-" * 50)
    
    # Test 2: No interesado  
    print("TEST 2: Forzar 'No Interesado' con subestado")
    payload2 = {
        "telefono": telefono_test,
        "noInteresado": True,
        "razonNoInteres": "Cliente no interesado - TEST",
        "codigoNoInteres": "otros"
    }
    
    print(f"Payload: {json.dumps(payload2, indent=2)}")
    
    try:
        response = requests.post(api_url, json=payload2, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        if response.status_code == 200:
            print("ESPERADO en BD:")
            print("- status_level_1: 'No Interesado'")
            print("- status_level_2: 'No da motivos'")
        
    except Exception as e:
        print(f"Error: {e}")

def crear_endpoint_test():
    """Crear un endpoint simple para verificar el estado actual"""
    print("\n=== VERIFICACION MANUAL NECESARIA ===")
    print("Necesitamos verificar manualmente en el dashboard:")
    print()
    print("1. Ve al dashboard de Railway")
    print("2. Busca el registro con teléfono 630474787")
    print("3. Verifica que campos tiene:")
    print("   - status_level_1: ¿qué valor tiene?")  
    print("   - status_level_2: ¿qué valor tiene?")
    print("   - razon_vuelta_a_llamar: ¿qué valor tiene?")
    print("   - razon_no_interes: ¿qué valor tiene?")
    print()
    print("4. Si status_level_2 está vacío, el problema es en la API")
    print("5. Si status_level_2 tiene valor, el problema es en el dashboard")

def test_multiple_phones():
    """Test con múltiples teléfonos para encontrar el patrón"""
    
    telefonos_test = [
        "630474787",  # MARIA CONCEPCIO 
        "617354291",  # ALBA GUTIERREZ
        "615029152",  # PAOLA MONTERO
    ]
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    print("\n=== TEST MÚLTIPLES TELÉFONOS ===")
    
    for telefono in telefonos_test:
        print(f"\nTesting {telefono}:")
        
        # Forzar como "Volver a llamar" 
        payload = {
            "telefono": telefono,
            "volverALlamar": True,
            "razonvueltaallamar": "DEBUG - Cliente no disponible",
            "codigoVolverLlamar": "interrupcion"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  Response: {result.get('message', 'OK')}")
            else:
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"  Exception: {e}")

def main():
    print("DEBUG DE SUBESTADOS FALTANTES")
    print("Este programa nos ayudará a entender por qué faltan subestados")
    print()
    
    test_api_response()
    crear_endpoint_test()
    test_multiple_phones()

if __name__ == "__main__":
    main()
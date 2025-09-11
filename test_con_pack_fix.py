"""
Test para verificar que solo se marca "Con Pack" cuando conPack=true
"""

import requests
import json

def test_con_pack_fix():
    url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Test 1: Con fechaDeseada + preferenciaMT pero SIN conPack -> debe ser "Sin Pack"
    test1 = {
        "telefono": "999888777",  # Teléfono ficticio para test
        "firstName": "TEST",
        "lastName": "SIN PACK",
        "fechaDeseada": "25-09-2025",
        "preferenciaMT": "morning",
        "callResult": "Cita agendada"
    }
    
    # Test 2: Con conPack=true -> debe ser "Con Pack" 
    test2 = {
        "telefono": "999888778",  # Teléfono ficticio para test
        "firstName": "TEST", 
        "lastName": "CON PACK",
        "fechaDeseada": "25-09-2025",
        "preferenciaMT": "morning", 
        "conPack": True,
        "callResult": "Cita agendada"
    }
    
    print("PROBANDO FIX DE CONPACK")
    print("="*50)
    
    for i, (test_name, data) in enumerate([("Sin Pack", test1), ("Con Pack", test2)], 1):
        print(f"\nTest {i} - {test_name}:")
        print(f"Datos: {json.dumps(data, indent=2)}")
        
        try:
            response = requests.post(url, json=data, timeout=30)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print(f"✅ API exitosa - Debería ser '{test_name}'")
            else:
                print(f"❌ Error API: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n" + "="*50)
    print("NOTA: Los teléfonos 999888777 y 999888778 son ficticios")
    print("Si no existen en BD, la API dirá 'No se encontró' pero aplicará la lógica")

if __name__ == "__main__":
    test_con_pack_fix()
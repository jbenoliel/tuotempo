#!/usr/bin/env python3
"""
Test final después de la corrección crítica de la API
"""
import requests
import json
import time

def test_fix_critico():
    """Test después de corregir el bug de cadenas vacías"""
    
    print("=== TEST DESPUÉS DE CORRECCIÓN CRÍTICA ===")
    print("Esperando que Railway complete el deploy...")
    time.sleep(15)  # Esperar deploy
    
    # Test con teléfono conocido
    telefono = "630474787"  # MARIA CONCEPCIO
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    print(f"Testing con {telefono}...")
    
    # Test 1: Forzar No Interesado
    payload = {
        "telefono": telefono,
        "noInteresado": True,
        "razonNoInteres": "TEST POST-FIX - No da motivos",
        "codigoNoInteres": "otros"
    }
    
    print("Test 1: No Interesado con subestado")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: API actualizada")
            print("Esperado en BD: status_level_2 = 'No da motivos'")
        else:
            print("ERROR en API")
        
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "="*50)
    print("IMPORTANTE: Ve al dashboard AHORA y verifica que:")
    print("- El registro 630474787 tiene status_level_2 = 'No da motivos'")
    print("- Si está vacío, el problema persiste")
    print("- Si tiene valor, la corrección funcionó")

if __name__ == "__main__":
    test_fix_critico()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar diferentes formatos de números de teléfono en el endpoint
"""
import requests
import json
from datetime import datetime

# URL base - utilizando el servicio principal según lo indicado en las memorias
BASE_URL = "https://tuotempo-apis-production.up.railway.app"
ENDPOINT = f"{BASE_URL}/api/actualizar_resultado"

def test_phone_formats():
    """Prueba el endpoint con diferentes formatos de número de teléfono."""
    print(f"Endpoint a probar: {ENDPOINT}")
    print(f"Fecha y hora de la prueba: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 50)
    
    # Diferentes formatos de número de teléfono para probar
    phone_formats = [
        {"telefono": "600000000"},           # Sin prefijo, como string
        {"numero_telefono": "600000000"},    # Campo alternativo
        {"phone": "600000000"},              # Nombre en inglés
        {"telefono": 600000000},             # Como número entero
        {"telefono": "+34600000000"},        # Con prefijo internacional
        {"telefono": "34600000000"},         # Con prefijo sin +
        {"telefono": "00600000000"},         # Formato alternativo
    ]
    
    # Payload base al que añadiremos cada formato de teléfono
    base_payload = {
        "resultado": "TEST_CONEXION",
        "id_llamada": 12345,
        "duracion": 60
    }
    
    for i, phone_format in enumerate(phone_formats, 1):
        # Combinamos el formato de teléfono con el payload base
        payload = {**base_payload, **phone_format}
        
        print(f"\nPrueba #{i}: {json.dumps(phone_format, indent=2)}")
        try:
            response = requests.post(ENDPOINT, json=payload, timeout=10)
            status = response.status_code
            print(f"Código de respuesta: {status}")
            
            # Intentar mostrar la respuesta como JSON, si no es posible, mostrar como texto
            try:
                resp_data = response.json()
                print(f"Respuesta: {json.dumps(resp_data, indent=2)}")
            except:
                print(f"Respuesta: {response.text[:200]}")
                
            if status == 200:
                print(f"✅ ÉXITO con el formato: {list(phone_format.keys())[0]} = {list(phone_format.values())[0]}")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            
    print("\n" + "=" * 50)
    print("Pruebas completadas. Si ninguna prueba tuvo éxito, es posible que:")
    print("1. El endpoint no esté implementado correctamente")
    print("2. El servicio 'actualizarllamadas' sea necesario para este endpoint")
    print("3. La ruta esté definida pero no registrada en el blueprint correcto")
    
    # Intentar hacer una petición GET para ver si devuelve información sobre el método
    try:
        print("\nProbando petición GET (para verificar si la ruta existe):")
        get_response = requests.get(ENDPOINT, timeout=5)
        print(f"Código: {get_response.status_code}")
        if get_response.status_code == 405:  # Method Not Allowed
            print("✅ La ruta EXISTE pero solo acepta POST (no GET)")
        else:
            print("❓ Respuesta inesperada para método GET")
    except Exception as e:
        print(f"Error al probar GET: {str(e)}")

if __name__ == "__main__":
    test_phone_formats()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script simplificado para probar específicamente el endpoint /api/actualizar_resultado
"""
import requests
import json

# URL base
BASE_URL = "https://tuotempo-apis-production.up.railway.app"

def test_endpoint():
    """Prueba el endpoint problemático con diferentes payloads y muestra información detallada."""
    endpoint = f"{BASE_URL}/api/actualizar_resultado"
    print(f"Probando endpoint: {endpoint}")
    
    # Lista de payloads para probar
    payloads = [
        # Formato 1 - Campos en español
        {
            "telefono": "+34600000000",
            "resultado": "TEST_CONEXION",
            "id_llamada": 123
        },
        # Formato 2 - Campos en inglés
        {
            "phone": "+34600000000",
            "result": "TEST_CONNECTION",
            "call_id": 123
        },
        # Formato 3 - Combinación de campos
        {
            "telefono": "+34600000000",
            "resultado": "TEST_CONEXION",
            "id_lead": 456
        },
        # Formato 4 - Campos adicionales
        {
            "telefono": "+34600000000",
            "resultado": "TEST_CONEXION",
            "id_llamada": 123,
            "duracion": 60,
            "fecha": "2025-07-17"
        }
    ]
    
    print("\n=== RESULTADOS DE LAS PRUEBAS ===")
    
    for i, payload in enumerate(payloads, 1):
        print(f"\nPrueba #{i}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            print(f"Código de respuesta: {response.status_code}")
            
            try:
                # Intentar obtener respuesta JSON
                resp_json = response.json()
                print(f"Respuesta JSON: {json.dumps(resp_json, indent=2)}")
            except:
                # Si no es JSON, mostrar texto
                print(f"Respuesta texto: {response.text[:300]}")
                
            if response.status_code == 200:
                print("✅ ÉXITO: Este formato de payload funciona correctamente")
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            
    print("\n=== COMPROBACIÓN DE RUTA ===")
    # Comprobar si la ruta existe pero espera un método diferente
    try:
        options_resp = requests.options(endpoint, timeout=5)
        head_resp = requests.head(endpoint, timeout=5)
        
        print(f"OPTIONS: {options_resp.status_code}")
        print(f"HEAD: {head_resp.status_code}")
        
        if options_resp.status_code < 404 or head_resp.status_code < 404:
            print("✅ La ruta existe pero puede requerir un formato específico de payload")
        else:
            print("❌ La ruta podría no estar registrada correctamente")
    except Exception as e:
        print(f"Error al verificar la ruta: {str(e)}")

if __name__ == "__main__":
    test_endpoint()

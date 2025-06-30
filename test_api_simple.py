#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simple para probar la API de resultados de llamadas.
"""

import requests
import json
import sys

# URL base para pruebas (cambiar según el entorno)
BASE_URL = "http://localhost:5000"  # Local

def test_api_status():
    """Prueba el endpoint /api/status"""
    url = f"{BASE_URL}/api/status"
    print(f"Probando endpoint: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Código de respuesta: {response.status_code}")
        print(f"Respuesta: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_obtener_resultados():
    """Prueba el endpoint /api/obtener_resultados"""
    url = f"{BASE_URL}/api/obtener_resultados"
    print(f"\nProbando endpoint: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Código de respuesta: {response.status_code}")
        print(f"Respuesta (primeros 200 caracteres): {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_actualizar_resultado():
    """Prueba el endpoint /api/actualizar_resultado con un teléfono de prueba"""
    url = f"{BASE_URL}/api/actualizar_resultado"
    print(f"\nProbando endpoint: {url}")
    
    # Primero obtenemos un teléfono para probar
    try:
        response = requests.get(f"{BASE_URL}/api/obtener_resultados", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("count", 0) > 0:
                telefono = data["contactos"][0]["telefono"]
                print(f"Usando teléfono de prueba: {telefono}")
                
                # Datos para actualizar
                payload = {
                    "telefono": telefono,
                    "no_interesado": True
                }
                
                # Enviar solicitud
                response = requests.post(url, json=payload, timeout=10)
                print(f"Código de respuesta: {response.status_code}")
                print(f"Respuesta: {response.text}")
                return response.status_code == 200
            else:
                print("No se encontraron teléfonos para probar")
                return False
        else:
            print(f"Error al obtener teléfonos: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== PRUEBA SIMPLE DE LA API ===")
    
    # Permitir cambiar la URL base desde la línea de comandos
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    
    print(f"Usando URL base: {BASE_URL}")
    
    # Probar endpoints
    status_ok = test_api_status()
    resultados_ok = test_obtener_resultados()
    actualizar_ok = test_actualizar_resultado()
    
    # Resumen
    print("\n=== RESUMEN DE PRUEBAS ===")
    print(f"API Status: {'✓ OK' if status_ok else '✗ FALLÓ'}")
    print(f"Obtener Resultados: {'✓ OK' if resultados_ok else '✗ FALLÓ'}")
    print(f"Actualizar Resultado: {'✓ OK' if actualizar_ok else '✗ FALLÓ'}")
    
    # Salir con código de error si alguna prueba falló
    sys.exit(0 if (status_ok and resultados_ok and actualizar_ok) else 1)

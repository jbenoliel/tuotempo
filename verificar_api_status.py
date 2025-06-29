#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script simple para verificar el estado de la API en Railway.
"""

import requests
import sys

# URL base de la API en Railway
API_BASE_URL = "https://tuotempo-production.up.railway.app"

def verificar_api_status():
    """Verifica que la API esté respondiendo correctamente"""
    print(f"Verificando API status en: {API_BASE_URL}/api/status")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/status")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("Respuesta exitosa (200 OK)")
            print(f"Contenido: {response.text}")
            return True
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"Error al conectar con la API: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n=== VERIFICACIÓN DE API STATUS ===\n")
    verificar_api_status()
    print("\n=== FIN DE VERIFICACIÓN ===\n")

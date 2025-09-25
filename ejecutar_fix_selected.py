#!/usr/bin/env python3
"""
Ejecutar corrección de estados 'selected' via API
"""

import requests
import json

def ejecutar_fix():
    """Llamar al endpoint para corregir estados selected"""
    try:
        print("=== EJECUTANDO CORRECCIÓN DE ESTADOS 'SELECTED' ===")

        # Llamar al endpoint
        url = "http://localhost:5000/api/calls/leads/fix-selected-status"
        response = requests.post(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"EXITO: {data['message']}")
            print(f"   - Leads corregidos: {data['fixed_count']}")
            print(f"   - Total antes: {data['total_before']}")
        else:
            print(f"ERROR: {response.status_code}")
            print(f"   Respuesta: {response.text}")

    except Exception as e:
        print(f"ERROR ejecutando correccion: {e}")

if __name__ == "__main__":
    ejecutar_fix()
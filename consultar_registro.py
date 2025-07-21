#!/usr/bin/env python3
"""
Consultar registros específicos para verificar status_level_2
"""
import requests
import json
import sys

def consultar_via_api(telefono):
    """Consultar registro vía API"""
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Payload de consulta (sin cambios)
    payload = {"telefono": telefono}
    headers = {'Content-Type': 'application/json'}
    
    print(f"=== CONSULTANDO REGISTRO {telefono} ===")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def actualizar_con_subestado(telefono):
    """Actualizar un registro con subestado específico"""
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    payload = {
        "telefono": telefono,
        "volverALlamar": True,
        "razonvueltaallamar": "Test de subestado - no disponible cliente",
        "codigoVolverLlamar": "interrupcion"
    }
    
    headers = {'Content-Type': 'application/json'}
    
    print(f"\n=== ACTUALIZANDO {telefono} CON SUBESTADO ===")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    # Teléfonos de prueba de la ejecución anterior
    telefonos_test = [
        "615029152",  # PAOLA MONTERO ROLDAN - Volver a llamar
        "630474787",  # MARIA CONCEPCIO - No Interesado  
        "639328670"   # FRANCISCA - Volver a llamar
    ]
    
    for telefono in telefonos_test:
        print(f"\n{'='*60}")
        print(f"PROCESANDO TELEFONO: {telefono}")
        print(f"{'='*60}")
        
        # Actualizar con subestado específico
        actualizar_con_subestado(telefono)
        
        print(f"\n{'-'*40}")
        input("Presiona Enter para continuar con el siguiente...")
    
    print(f"\n{'='*60}")
    print("VERIFICACION COMPLETADA")
    print("Verifica en el dashboard que los subestados aparecen correctamente:")
    print("- status_level_1: 'Volver a llamar'")
    print("- status_level_2: 'no disponible cliente'")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
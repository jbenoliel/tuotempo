#!/usr/bin/env python3
"""
Script para probar manualmente la API de selección de leads
"""
import requests
import json

def probar_api_seleccion():
    """Probar la API de selección de leads con 'Volver a llamar'"""
    
    # URL del servidor local
    base_url = "http://localhost:8080"
    
    print("PROBANDO API DE SELECCIÓN")
    print("="*40)
    
    # Datos para la API
    data = {
        "status_field": "status_level_1",
        "status_value": "Volver a llamar",
        "selected": True
    }
    
    print(f"1. Enviando POST a {base_url}/leads/select-by-status")
    print(f"   Datos: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/leads/select-by-status",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n2. RESPUESTA:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Response Body: {json.dumps(result, indent=2)}")
            
            if result.get('success'):
                selected_count = result.get('selected_count', 0)
                print(f"\n✅ API FUNCIONÓ: {selected_count} leads seleccionados")
                if selected_count == 0:
                    print("⚠️  PERO NO SE SELECCIONARON LEADS - Revisar condiciones")
            else:
                print(f"❌ API retornó success=False: {result}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Body: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se puede conectar al servidor")
        print("   ¿Está ejecutándose el servidor en localhost:8080?")
        print("   Ejecuta: python app.py")
    except requests.exceptions.Timeout:
        print("❌ ERROR: Timeout - el servidor tardó demasiado")
    except Exception as e:
        print(f"❌ ERROR INESPERADO: {e}")

def verificar_servidor():
    """Verificar si el servidor está corriendo"""
    try:
        response = requests.get("http://localhost:8080/", timeout=5)
        print(f"✅ Servidor corriendo - Status: {response.status_code}")
        return True
    except:
        print("❌ Servidor NO disponible en localhost:8080")
        return False

if __name__ == "__main__":
    print("Verificando servidor...")
    if verificar_servidor():
        print()
        probar_api_seleccion()
    else:
        print("\nInicia el servidor con: python app.py")
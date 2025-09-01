#!/usr/bin/env python3
"""
Script de prueba para verificar que la UI funciona después de las correcciones.
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_api_endpoints():
    """Prueba los endpoints principales de la API"""
    print("🧪 Probando endpoints de API...")
    
    endpoints = [
        "/api/calls/status",
        "/api/calls/leads", 
        "/calls-manager"
    ]
    
    for endpoint in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"  Probando: {url}")
            
            if endpoint == "/calls-manager":
                # Para la página HTML, solo verificar que responde
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"    ✅ {endpoint} - OK (HTML)")
                else:
                    print(f"    ❌ {endpoint} - Error {response.status_code}")
            else:
                # Para APIs JSON
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    ✅ {endpoint} - OK (JSON)")
                    except:
                        print(f"    ⚠️  {endpoint} - Respuesta no JSON")
                else:
                    print(f"    ❌ {endpoint} - Error {response.status_code}")
                    
        except requests.exceptions.ConnectionError:
            print(f"    ❌ {endpoint} - No se pudo conectar (¿servidor corriendo?)")
        except Exception as e:
            print(f"    ❌ {endpoint} - Error: {e}")

def test_leads_selection():
    """Prueba la funcionalidad de selección de leads"""
    print("\n🎯 Probando API de selección de leads...")
    
    try:
        # Primero obtener algunos leads
        leads_response = requests.get(f"{BASE_URL}/api/calls/leads", timeout=5)
        
        if leads_response.status_code == 200:
            leads_data = leads_response.json()
            leads = leads_data.get('leads', [])
            
            if leads:
                # Probar seleccionar el primer lead
                lead_id = leads[0]['id']
                selection_data = {
                    "lead_ids": [lead_id],
                    "selected": True
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/calls/leads/select",
                    json=selection_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    print("    ✅ Selección de leads - OK")
                else:
                    print(f"    ❌ Selección de leads - Error {response.status_code}")
            else:
                print("    ⚠️  No hay leads para probar selección")
        else:
            print(f"    ❌ No se pudieron obtener leads - Error {leads_response.status_code}")
            
    except Exception as e:
        print(f"    ❌ Error probando selección: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de la UI corregida...\n")
    
    test_api_endpoints()
    test_leads_selection()
    
    print("\n" + "="*50)
    print("✅ Pruebas completadas!")
    print("\n📝 Instrucciones:")
    print("1. Si todas las pruebas pasaron, abre http://localhost:5000/calls-manager")
    print("2. Prueba seleccionar 'Seleccionar Todo' - los leads NO deberían desaparecer")
    print("3. Los errores ahora deberían mostrarse como toast notifications")
    print("="*50)
#!/usr/bin/env python3
"""
Script para verificar que todos los endpoints de la API de llamadas estén funcionando correctamente.
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"  # Cambia esto si tu servidor está en otro puerto
API_BASE = f"{BASE_URL}/api/calls"

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Prueba un endpoint específico."""
    url = f"{API_BASE}{endpoint}"
    
    print(f"🔍 Probando {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Método {method} no soportado")
            return False
        
        print(f"   Status: {response.status_code}")
        
        # Mostrar contenido de respuesta siempre (para debugging)
        try:
            result = response.json()
            if response.status_code != expected_status:
                print(f"   📄 Error Response: {json.dumps(result, indent=2)}")
            else:
                # Solo mostrar un preview si es exitoso
                preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                print(f"   📄 Response: {preview}")
        except:
            print(f"   📄 Response (text): {response.text[:200]}...")
        
        if response.status_code == expected_status:
            print(f"   ✅ OK")
            return True
        else:
            print(f"   ❌ Error - Expected {expected_status}, got {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Error de conexión - ¿Está el servidor ejecutándose en {BASE_URL}?")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("🚀 Verificando endpoints de la API de llamadas...")
    print(f"📡 URL Base: {API_BASE}")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print("-" * 60)
    
    tests_passed = 0
    total_tests = 0
    
    # Lista de endpoints a probar
    endpoints_to_test = [
        ("GET", "/status", None, 200),
        ("GET", "/leads", None, 200),
        ("GET", "/configuration", None, 200),
        ("GET", "/test-connection", None, 200),
        ("GET", "/test/connection", None, 200),
        ("POST", "/configuration", {"maxConcurrentCalls": 3}, 200),
        ("GET", "/pearl/campaigns", None, [200, 502, 503]),  # Puede fallar si Pearl no está configurado
    ]
    
    for method, endpoint, data, expected_status in endpoints_to_test:
        total_tests += 1
        
        # Manejar múltiples códigos de estado esperados
        if isinstance(expected_status, list):
            success = False
            for status in expected_status:
                if test_endpoint(method, endpoint, data, status):
                    success = True
                    break
            if success:
                tests_passed += 1
        else:
            if test_endpoint(method, endpoint, data, expected_status):
                tests_passed += 1
        
        print()  # Línea vacía entre tests
    
    print("-" * 60)
    print(f"📊 Resultados: {tests_passed}/{total_tests} tests pasaron")
    
    if tests_passed == total_tests:
        print("🎉 ¡Todos los endpoints funcionan correctamente!")
        return 0
    else:
        print("⚠️ Algunos endpoints tienen problemas")
        return 1

if __name__ == "__main__":
    sys.exit(main())

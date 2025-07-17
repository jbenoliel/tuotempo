#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar servicios Railway y endpoints API
"""
import requests
import os
import json
import time
from requests.exceptions import RequestException
from urllib.parse import urlparse

# Normalizar el nombre del servicio (función mencionada en las memorias)
def normalize_service_name(name):
    """Normaliza el nombre del servicio Railway para consistencia."""
    if name is None:
        return None
    return name.lower().replace(' ', '-')

# Detectar URL base actual
def get_base_url():
    """Intenta determinar la URL base correcta para las peticiones."""
    # Opciones de URL base según la memoria
    possible_urls = [
        "https://tuotempo-apis-production.up.railway.app",
        "https://web.up.railway.app",
        "https://dashboard.up.railway.app",
        "https://tuotempo-apis.up.railway.app",
    ]
    
    for url in possible_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"\033[92mURL base detectada automáticamente: {url}\033[0m")
                return url
        except RequestException:
            continue
    
    # Si no encontramos una URL válida, usamos la primera como fallback
    print(f"\033[93mNo se pudo detectar automáticamente la URL base. Usando: {possible_urls[0]}\033[0m")
    return possible_urls[0]

# Identificar servicios Railway activos
def check_railway_services(base_url):
    """Identifica qué servicios Railway están actualmente activos."""
    domain = urlparse(base_url).netloc
    project_name = domain.split('.')[0]
    
    print(f"Proyecto Railway detectado: \033[94m{project_name}\033[0m")
    
    # Verificamos si también existe el servicio de actualizarllamadas
    actualizarllamadas_url = f"https://actualizarllamadas.up.railway.app"
    try:
        response = requests.get(actualizarllamadas_url, timeout=5)
        if response.status_code < 500:  # Incluso un 404 significa que el servicio existe
            print(f"\033[92mServicio secundario 'actualizarllamadas' detectado y activo\033[0m")
            return [project_name, "actualizarllamadas"]
    except RequestException:
        pass
    
    print(f"\033[93mNo se detectó el servicio secundario 'actualizarllamadas'\033[0m")
    return [project_name]

# Probar varios formatos de payload para el endpoint problemático
def test_actualizar_resultado_endpoint(base_url):
    """Prueba diferentes variaciones de payload para el endpoint actualizar_resultado."""
    url = f"{base_url}/api/actualizar_resultado"
    print(f"\nDiagnosticando endpoint: \033[94m{url}\033[0m")
    
    payloads = [
        # Prueba 1: Campos básicos
        {
            "phone": "+34600000000",
            "result": "TEST_CALL",
            "lead_id": 1
        },
        # Prueba 2: Variación de nombres de campo
        {
            "telefono": "+34600000000",
            "resultado": "TEST_CALL",
            "id_lead": 1
        },
        # Prueba 3: Más campos potenciales
        {
            "phone": "+34600000000",
            "result": "TEST_CALL",
            "lead_id": 1,
            "call_id": "test-123",
            "duration": 60,
            "timestamp": int(time.time())
        },
        # Prueba 4: Estructura mínima
        {
            "phone": "+34600000000"
        }
    ]
    
    for i, payload in enumerate(payloads, 1):
        print(f"\nPrueba {i} con payload:")
        print(json.dumps(payload, indent=2))
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            print(f"Respuesta: \033[93mCódigo {response.status_code}\033[0m")
            
            if response.status_code == 200:
                print("\033[92m¡Éxito! Este formato de payload funciona.\033[0m")
                print(f"Contenido de la respuesta: {response.text[:200]}")
                return True
            
            # Intentar extraer mensaje de error
            try:
                error_data = response.json()
                print(f"Mensaje de error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Cuerpo de la respuesta: {response.text[:200]}")
        
        except RequestException as e:
            print(f"\033[91mError de conexión: {e}\033[0m")
    
    return False

# Verificar disponibilidad general de la API
def check_api_health(base_url):
    """Verifica la salud general de la API y sus principales endpoints."""
    endpoints = [
        "/",
        "/api",
        "/api/health",
        "/health",
        "/status"
    ]
    
    print("\nVerificando endpoints de salud general:")
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            status = "✅" if response.status_code < 400 else "❌"
            print(f"{status} {url} - Código: {response.status_code}")
        except RequestException:
            print(f"❌ {url} - Error de conexión")

def main():
    """Función principal para ejecutar el diagnóstico completo."""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE SERVICIOS RAILWAY Y API")
    print("=" * 60)
    
    # Paso 1: Determinar la URL base correcta
    base_url = get_base_url()
    
    # Paso 2: Identificar servicios activos
    active_services = check_railway_services(base_url)
    
    # Paso 3: Verificar salud general de la API
    check_api_health(base_url)
    
    # Paso 4: Probar específicamente el endpoint problemático
    success = test_actualizar_resultado_endpoint(base_url)
    
    print("\n" + "=" * 60)
    if success:
        print("\033[92m✅ Diagnóstico completado con éxito!\033[0m")
    else:
        print("\033[93m⚠️ Diagnóstico completado con problemas.\033[0m")
        print("Recomendaciones:")
        print("1. Verifica que el servicio 'actualizarllamadas' esté desplegado")
        print("2. Revisa la ruta /api/actualizar_resultado en el código")
        print("3. Asegúrate que el blueprint 'resultado_api' esté registrado")
    print("=" * 60)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script para probar las APIs de monitoreo y verificación en local
sin depender de la interfaz web.
"""

import requests
import json
from pprint import pprint
import time

# URLs base para testing local
BASE_URL = "http://localhost:5000"

def test_daemon_apis():
    """Prueba las APIs de monitoreo del daemon de reservas automáticas"""
    print("\n=== PROBANDO APIs DE MONITOREO DEL DAEMON ===")
    
    # 1. API de estado completo del daemon
    print("\n1. Consultando estado del daemon...")
    try:
        response = requests.get(f"{BASE_URL}/api/daemon/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ API de estado responde correctamente")
            print("Último heartbeat:", data.get('last_heartbeat', 'N/A'))
            print("Estado:", data.get('status', 'N/A'))
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error al conectar con API de estado: {e}")
    
    # 2. API de healthcheck del daemon
    print("\n2. Consultando healthcheck del daemon...")
    try:
        response = requests.get(f"{BASE_URL}/api/daemon/healthcheck")
        if response.status_code == 200:
            print("✅ API de healthcheck responde correctamente (200 OK)")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error al conectar con API de healthcheck: {e}")
    
    # 3. API de estadísticas del daemon
    print("\n3. Consultando estadísticas del daemon...")
    try:
        response = requests.get(f"{BASE_URL}/api/daemon/stats")
        if response.status_code == 200:
            data = response.json()
            print("✅ API de estadísticas responde correctamente")
            print("Total de ciclos:", data.get('total_cycles', 'N/A'))
            print("Leads procesados:", data.get('leads_processed', 'N/A'))
            print("Reservas exitosas:", data.get('successful_reservations', 'N/A'))
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error al conectar con API de estadísticas: {e}")
    
    # 4. API de alertas del daemon
    print("\n4. Consultando alertas del daemon...")
    try:
        response = requests.get(f"{BASE_URL}/api/daemon/alert")
        if response.status_code == 200:
            data = response.json()
            print("✅ API de alertas responde correctamente")
            print("Hay alertas críticas:", data.get('has_critical', False))
            print("Hay alertas de advertencia:", data.get('has_warning', False))
            if 'alerts' in data:
                print("Alertas activas:", len(data['alerts']))
                for alert in data.get('alerts', []):
                    print(f"  - {alert.get('type', 'desconocido')}: {alert.get('message', 'Sin mensaje')}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error al conectar con API de alertas: {e}")

def test_railway_verification_apis():
    """Prueba las APIs de verificación de servicios Railway"""
    print("\n=== PROBANDO APIs DE VERIFICACIÓN RAILWAY ===")
    
    # 1. API de configuración de verificación
    print("\n1. Consultando configuración de verificación Railway...")
    try:
        response = requests.get(f"{BASE_URL}/api/railway/verification/config")
        if response.status_code == 200:
            data = response.json()
            print("✅ API de configuración responde correctamente")
            print("Servicios a verificar:", len(data.get('services', [])))
            for service in data.get('services', []):
                print(f"  - {service.get('name', 'desconocido')}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error al conectar con API de configuración: {e}")
    
    # 2. Iniciar verificación rápida
    print("\n2. Iniciando verificación rápida...")
    try:
        response = requests.post(f"{BASE_URL}/api/railway/verification/quick")
        if response.status_code == 200:
            data = response.json()
            print("✅ Verificación rápida iniciada correctamente")
            verification_id = data.get('verification_id')
            print(f"ID de verificación: {verification_id}")
            
            # Esperar resultados
            print("Esperando resultados (5 segundos)...")
            time.sleep(5)
            
            # Consultar estado
            print("\n3. Consultando estado de verificación...")
            status_response = requests.get(f"{BASE_URL}/api/railway/verification/status/{verification_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print("✅ Estado de verificación obtenido correctamente")
                print("Estado:", status_data.get('status', 'desconocido'))
                print("Progreso:", f"{status_data.get('progress', 0)}%")
                
                # Consultar resultados si está completo
                if status_data.get('status') == 'completed':
                    print("\n4. Consultando resultados de verificación...")
                    results_response = requests.get(f"{BASE_URL}/api/railway/verification/results/{verification_id}")
                    if results_response.status_code == 200:
                        results_data = results_response.json()
                        print("✅ Resultados obtenidos correctamente")
                        print("Servicios verificados:", len(results_data.get('results', [])))
                        for result in results_data.get('results', []):
                            service_name = result.get('service_name', 'desconocido')
                            status = result.get('status', 'desconocido')
                            print(f"  - {service_name}: {status}")
                    else:
                        print(f"❌ Error {results_response.status_code} al obtener resultados")
            else:
                print(f"❌ Error {status_response.status_code} al consultar estado")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error al iniciar verificación rápida: {e}")

if __name__ == "__main__":
    print("======================================================")
    print("PRUEBA DE APIs DE MONITOREO Y VERIFICACIÓN EN LOCAL")
    print("======================================================")
    
    # Asegurarse de que la aplicación Flask esté ejecutándose en http://localhost:5000
    print("\nComprobando conexión a la aplicación Flask...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Aplicación Flask accesible")
        else:
            print(f"⚠️ Aplicación Flask responde con código {response.status_code}")
    except Exception as e:
        print(f"❌ No se puede conectar con la aplicación Flask: {e}")
        print("⚠️ Asegúrate de que la aplicación esté ejecutándose en http://localhost:5000")
        exit(1)
    
    # Probar APIs de monitoreo del daemon
    test_daemon_apis()
    
    # Probar APIs de verificación Railway
    test_railway_verification_apis()
    
    print("\n======================================================")
    print("RESUMEN DE PRUEBAS")
    print("======================================================")
    print("Las pruebas han finalizado. Revisa los resultados anteriores para ver el estado de:")
    print("1. APIs de monitoreo del daemon de reservas automáticas")
    print("2. APIs de verificación de servicios Railway")
    print("\nSi todas las pruebas pasaron, los sistemas están listos para ser desplegados en Railway.")
    print("Si hay errores, corrige los problemas antes de desplegar.")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simple para verificar si el servidor Flask está escuchando correctamente.
"""

import socket
import requests
import sys
import time

def check_port_open(host, port):
    """Verifica si un puerto está abierto en el host especificado"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def test_endpoint(url):
    """Prueba un endpoint específico"""
    print(f"Probando: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"  Código de estado: {response.status_code}")
        print(f"  Respuesta: {response.text[:100]}...")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("  Error de conexión: No se pudo conectar al servidor")
        return False
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def main():
    """Función principal"""
    host = "localhost"
    port = 5000
    
    print(f"Verificando si el puerto {port} está abierto en {host}...")
    if check_port_open(host, port):
        print(f"✅ El puerto {port} está abierto en {host}")
    else:
        print(f"❌ El puerto {port} NO está abierto en {host}")
        print("Posibles causas:")
        print("1. El servidor Flask no está en ejecución")
        print("2. El servidor está escuchando en un puerto diferente")
        print("3. El servidor está escuchando solo en una interfaz específica")
        print("4. Un firewall está bloqueando el acceso al puerto")
        return
    
    # Probar algunos endpoints básicos
    base_url = f"http://{host}:{port}"
    endpoints = [
        "/",
        "/api/status",
        "/api/obtener_resultados"
    ]
    
    print("\nProbando endpoints básicos:")
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        test_endpoint(url)
        time.sleep(1)  # Pequeña pausa entre solicitudes

if __name__ == "__main__":
    main()

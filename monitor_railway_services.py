#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monitor de servicios Railway para Tuotempo
Verifica el estado de todos los servicios y endpoints principales
"""
import os
import sys
import requests
import json
import time
from datetime import datetime
import argparse

# Colores para la consola
class Colors:
    OK = '\033[92m'       # Verde
    WARNING = '\033[93m'  # Amarillo
    ERROR = '\033[91m'    # Rojo
    BLUE = '\033[94m'     # Azul
    ENDC = '\033[0m'      # Reset
    BOLD = '\033[1m'      # Negrita

def normalize_service_name(name):
    """Normaliza el nombre del servicio Railway para consistencia."""
    if name is None:
        return None
    return name.lower().replace(' ', '-')

def print_header(text):
    """Imprime un encabezado formateado."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.ENDC}\n")

def print_success(text):
    """Imprime un mensaje de éxito."""
    print(f"{Colors.OK}✅ {text}{Colors.ENDC}")

def print_warning(text):
    """Imprime un mensaje de advertencia."""
    print(f"{Colors.WARNING}⚠️ {text}{Colors.ENDC}")

def print_error(text):
    """Imprime un mensaje de error."""
    print(f"{Colors.ERROR}❌ {text}{Colors.ENDC}")

def check_service(url, method="GET", data=None, name=None, expected_error=None):
    """Verifica el estado de un servicio o endpoint.
    
    Args:
        url (str): URL del servicio a verificar
        method (str): Método HTTP a utilizar (GET, POST, etc.)
        data (dict): Datos a enviar en la petición (para POST)
        name (str): Nombre descriptivo del servicio
        expected_error (str): Mensaje de error esperado (para validar comportamiento)
        
    Returns:
        tuple: (is_ok, status_code, response_text)
    """
    service_name = name if name else url
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            return False, 0, f"Método no soportado: {method}"
            
        status = response.status_code
        
        # Intentar obtener respuesta como JSON
        response_text = ""
        try:
            resp_data = response.json()
            response_text = json.dumps(resp_data, indent=2)
            
            # Si esperamos un mensaje de error específico, verificar si está presente
            if expected_error and "error" in resp_data:
                if expected_error in resp_data["error"]:
                    return True, status, f"Error esperado: {resp_data['error']}"
                    
        except:
            response_text = response.text[:100] + "..." if len(response.text) > 100 else response.text
            
        # Determinar si el servicio está OK basado en el código de estado
        is_ok = status < 400 or (expected_error and status < 500)
        
        return is_ok, status, response_text
        
    except Exception as e:
        return False, 0, str(e)

def monitor_services(base_url=None, verbose=False, check_all=False, check_lead=None):
    """Monitorea todos los servicios Railway de Tuotempo.
    
    Args:
        base_url (str): URL base para los servicios (opcional)
        verbose (bool): Si True, muestra información detallada
        check_all (bool): Si True, verifica todos los endpoints
        check_lead (str): Número de teléfono específico para verificar
    """
    # Determinar URL base
    if not base_url:
        base_url = os.environ.get("RAILWAY_STATIC_URL", "tuotempo-apis-production.up.railway.app")
    
    # Asegurar que tiene el prefijo https://
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
        
    # Eliminar cualquier trailing slash
    base_url = base_url.rstrip('/')
    
    print_header("MONITOR DE SERVICIOS RAILWAY PARA TUOTEMPO")
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL base: {base_url}")
    
    # Servicios principales a verificar
    services = [
        {"url": base_url, "method": "GET", "name": "Servicio Principal"},
        {"url": f"{base_url}/api", "method": "GET", "name": "API Base"},
    ]
    
    # Verificar también servicio actualizarllamadas
    actualizarllamadas_url = base_url.replace("tuotempo-apis-production", "actualizarllamadas")
    services.append({
        "url": actualizarllamadas_url, 
        "method": "GET", 
        "name": "Servicio ActualizarLlamadas"
    })
    
    # Si se solicita verificación completa o un lead específico
    if check_all or check_lead:
        # Preparar payload para el endpoint actualizar_resultado
        lead_phone = check_lead if check_lead else "600000000"
        payload = {
            "telefono": lead_phone,
            "resultado": "TEST_MONITOR",
            "id_llamada": int(time.time())
        }
        
        # Añadir endpoints adicionales
        services.extend([
            {
                "url": f"{base_url}/api/actualizar_resultado", 
                "method": "POST", 
                "name": "Endpoint ActualizarResultado", 
                "data": payload,
                "expected_error": "No se encontró ningún lead" if not check_lead else None
            }
        ])
        
        if check_all:
            # Añadir otros endpoints importantes si check_all es True
            services.extend([
                {"url": f"{base_url}/api/health", "method": "GET", "name": "Health Check"},
                {"url": f"{base_url}/api/status", "method": "GET", "name": "Status Check"},
                # Añadir aquí otros endpoints a verificar
            ])
    
    # Verificar cada servicio
    all_ok = True
    results = []
    
    print_header("RESULTADOS DE LA VERIFICACIÓN")
    
    for service in services:
        name = service["name"]
        url = service["url"]
        method = service.get("method", "GET")
        data = service.get("data", None)
        expected_error = service.get("expected_error", None)
        
        is_ok, status, response_text = check_service(
            url, method, data, name, expected_error
        )
        
        # Almacenar resultado
        results.append({
            "name": name,
            "url": url,
            "status": status,
            "is_ok": is_ok,
            "response": response_text
        })
        
        # Actualizar estado general
        if not is_ok:
            all_ok = False
        
        # Mostrar resultado
        status_text = f"({status})" if status else ""
        if is_ok:
            print_success(f"{name}: OK {status_text}")
        else:
            print_error(f"{name}: ERROR {status_text}")
            
        # Si se solicita modo verbose, mostrar detalles
        if verbose and (response_text or not is_ok):
            print(f"  URL: {url}")
            if data:
                print(f"  Payload: {json.dumps(data, indent=2)}")
            if response_text:
                print(f"  Respuesta: {response_text}")
            print("")
    
    # Mostrar resumen final
    print_header("RESUMEN")
    if all_ok:
        print_success("Todos los servicios verificados están operativos.")
    else:
        print_warning("Algunos servicios presentan problemas.")
        
    return all_ok, results

def main():
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Monitor de servicios Railway para Tuotempo")
    parser.add_argument("--url", help="URL base para los servicios")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar información detallada")
    parser.add_argument("--all", "-a", action="store_true", help="Verificar todos los endpoints")
    parser.add_argument("--lead", "-l", help="Teléfono específico para verificar")
    
    args = parser.parse_args()
    
    # Ejecutar monitorización
    all_ok, _ = monitor_services(
        base_url=args.url,
        verbose=args.verbose,
        check_all=args.all,
        check_lead=args.lead
    )
    
    # Salir con código apropiado
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()

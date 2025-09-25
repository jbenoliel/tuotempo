"""
Script para diagnosticar qué endpoints están disponibles en la aplicación.
Útil para debuggear problemas de 404 en Railway.
"""

import requests
import json
from datetime import datetime

def check_endpoint_availability(base_url):
    """
    Verifica qué endpoints están disponibles en la aplicación.

    Args:
        base_url (str): URL base de la aplicación (ej: https://tuotempo-apis-production.up.railway.app)
    """
    print(f"=== DIAGNÓSTICO DE ENDPOINTS ===")
    print(f"Base URL: {base_url}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Lista de endpoints a verificar
    endpoints_to_check = [
        # Endpoints principales
        {"path": "/", "method": "GET", "description": "Root endpoint"},
        {"path": "/health", "method": "GET", "description": "Health check"},

        # API de TuoTempo
        {"path": "/api/status", "method": "GET", "description": "Status API tuotempo"},
        {"path": "/api/slots", "method": "GET", "description": "Slots API", "params": {"centro_id": "test", "fecha_inicio": "25-12-2024", "phone": "123456789"}},
        {"path": "/api/reservar", "method": "POST", "description": "Reservar API"},

        # API de Resultado de Llamadas (el que está fallando)
        {"path": "/api/actualizar_resultado", "method": "POST", "description": "Actualizar resultado llamada"},
        {"path": "/api/obtener_resultados", "method": "GET", "description": "Obtener resultados"},
        {"path": "/api/leads_reserva_automatica", "method": "GET", "description": "Leads reserva automática"},

        # API de Centros
        {"path": "/api/centros", "method": "GET", "description": "API Centros", "params": {"cp": "28001"}},

        # Nuevos endpoints de logging
        {"path": "/api/logs/tuotempo", "method": "GET", "description": "Logs tuotempo APIs"},

        # Otros endpoints
        {"path": "/api/daemon/status", "method": "GET", "description": "Daemon status"},
        {"path": "/api/railway/verification", "method": "GET", "description": "Railway verification"},
    ]

    results = []

    for endpoint in endpoints_to_check:
        path = endpoint["path"]
        method = endpoint["method"]
        description = endpoint["description"]
        params = endpoint.get("params", {})

        url = f"{base_url}{path}"

        print(f"\n[CHECK] Verificando: {method} {path}")
        print(f"   Descripcion: {description}")

        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, json={"test": "data"}, timeout=10)
            else:
                response = requests.request(method, url, timeout=10)

            status_code = response.status_code

            if status_code == 404:
                print(f"   [ERROR] 404: Endpoint no encontrado")
                result_status = "NOT_FOUND"
            elif status_code >= 500:
                print(f"   [ERROR] {status_code}: Error del servidor")
                result_status = "SERVER_ERROR"
            elif status_code >= 400:
                print(f"   [WARN] {status_code}: Error de cliente (pero endpoint existe)")
                result_status = "CLIENT_ERROR"
            elif status_code < 300:
                print(f"   [OK] {status_code}: Endpoint disponible")
                result_status = "SUCCESS"
            else:
                print(f"   [INFO] {status_code}: Respuesta inesperada")
                result_status = "UNEXPECTED"

            # Intentar mostrar contenido de respuesta si es JSON pequeño
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    content = response.json()
                    if len(str(content)) < 200:
                        print(f"   [RESPONSE] {content}")
                elif len(response.text) < 100:
                    print(f"   [RESPONSE] {response.text[:100]}")
            except:
                pass

        except requests.exceptions.Timeout:
            print(f"   [TIMEOUT] El endpoint no respondio en 10 segundos")
            result_status = "TIMEOUT"
        except requests.exceptions.ConnectionError:
            print(f"   [CONNECTION_ERROR] No se pudo conectar")
            result_status = "CONNECTION_ERROR"
        except Exception as e:
            print(f"   [ERROR] {str(e)}")
            result_status = "ERROR"

        results.append({
            "path": path,
            "method": method,
            "description": description,
            "status": result_status,
            "timestamp": datetime.now().isoformat()
        })

    # Resumen final
    print(f"\n{'='*50}")
    print("RESUMEN:")
    print(f"{'='*50}")

    status_counts = {}
    for result in results:
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in status_counts.items():
        status_label = {
            "SUCCESS": "[OK]",
            "CLIENT_ERROR": "[WARN]",
            "NOT_FOUND": "[ERROR]",
            "SERVER_ERROR": "[ERROR]",
            "TIMEOUT": "[TIMEOUT]",
            "CONNECTION_ERROR": "[CONNECTION_ERROR]",
            "ERROR": "[ERROR]"
        }
        label = status_label.get(status, "[INFO]")
        print(f"{label} {status}: {count} endpoints")

    # Mostrar endpoints problemáticos
    problematic = [r for r in results if r["status"] in ["NOT_FOUND", "SERVER_ERROR", "ERROR"]]
    if problematic:
        print(f"\nENDPOINTS CON PROBLEMAS:")
        for result in problematic:
            print(f"   {result['method']} {result['path']} - {result['status']}")

    return results

def main():
    """Función principal."""
    import sys

    # URL por defecto
    base_url = "https://tuotempo-apis-production.up.railway.app"

    # Permitir URL personalizada como argumento
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print("DIAGNOSTICO DE ENDPOINTS - TuoTempo APIs")
    print("Este script verifica que endpoints estan disponibles en Railway")
    print()

    results = check_endpoint_availability(base_url)

    # Guardar resultados en archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diagnostico_endpoints_{timestamp}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "base_url": base_url,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }, f, indent=2, ensure_ascii=False)
        print(f"\nResultados guardados en: {filename}")
    except Exception as e:
        print(f"\nNo se pudo guardar el archivo: {e}")

if __name__ == "__main__":
    main()
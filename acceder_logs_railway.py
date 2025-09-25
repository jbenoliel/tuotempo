"""
Script para acceder a los logs de tuotempo en Railway.

Este script muestra diferentes formas de acceder a los logs cuando la aplicación
está desplegada en Railway.
"""

import requests
import json
import os

def acceder_logs_via_api(railway_url, max_lines=20, hours_ago=1):
    """
    Accede a los logs a través del endpoint de la API.

    Args:
        railway_url (str): URL base de la aplicación en Railway
        max_lines (int): Número máximo de líneas a obtener
        hours_ago (int): Horas hacia atrás para filtrar logs

    Returns:
        dict: Respuesta con los logs
    """
    try:
        url = f"{railway_url}/api/logs/tuotempo"
        params = {
            'max_lines': max_lines,
            'hours_ago': hours_ago
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a los logs via API: {e}")
        return None

def imprimir_logs_formateados(logs_response):
    """
    Imprime los logs de forma legible.

    Args:
        logs_response (dict): Respuesta del endpoint de logs
    """
    if not logs_response or not logs_response.get('success'):
        print("No se pudieron obtener los logs")
        return

    logs = logs_response.get('logs', [])
    total = logs_response.get('total_logs', 0)

    print(f"\n=== LOGS DE TUOTEMPO APIs ({total} entradas) ===")
    print(f"Parámetros: {logs_response.get('parameters', {})}")
    print("=" * 60)

    if not logs:
        print("No hay logs disponibles")
        return

    for i, log in enumerate(logs, 1):
        if "raw_line" in log:
            print(f"{i:2d}. {log['raw_line']}")
        else:
            timestamp = log.get("timestamp", "N/A")[:19]  # Solo fecha y hora
            function = log.get("function", log.get("method", "N/A"))
            success = "✓" if log.get("success") else "✗"

            print(f"{i:2d}. [{timestamp}] {function} {success}")

            # Mostrar parámetros si existen
            params = log.get("params") or log.get("kwargs")
            if params and isinstance(params, dict):
                # Solo mostrar parámetros más relevantes
                relevant_params = {}
                for key in ['areaId', 'activityid', 'start_date', 'phone']:
                    if key in params:
                        relevant_params[key] = params[key]
                if relevant_params:
                    print(f"    Params: {relevant_params}")

            # Mostrar errores si existen
            error = log.get("error")
            if error:
                print(f"    Error: {error[:100]}{'...' if len(error) > 100 else ''}")

def generar_estadisticas_logs(logs_response):
    """
    Genera estadísticas de los logs.

    Args:
        logs_response (dict): Respuesta del endpoint de logs
    """
    if not logs_response or not logs_response.get('success'):
        return

    logs = logs_response.get('logs', [])

    successful_calls = sum(1 for log in logs if log.get("success"))
    failed_calls = sum(1 for log in logs if log.get("success") is False)

    functions_count = {}
    methods_count = {}

    for log in logs:
        # Contar funciones
        func = log.get("function")
        if func:
            functions_count[func] = functions_count.get(func, 0) + 1

        # Contar métodos HTTP
        method = log.get("method")
        if method:
            methods_count[method] = methods_count.get(method, 0) + 1

    print(f"\n=== ESTADÍSTICAS ===")
    print(f"Total de llamadas: {len(logs)}")
    print(f"Exitosas: {successful_calls}")
    print(f"Fallidas: {failed_calls}")

    if functions_count:
        print("\nFunciones más llamadas:")
        for func, count in sorted(functions_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {func}: {count}")

    if methods_count:
        print("\nMétodos HTTP:")
        for method, count in sorted(methods_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {method}: {count}")

def ejemplo_monitoreo_continuo(railway_url, intervalo_minutos=5):
    """
    Ejemplo de monitoreo continuo de logs.

    Args:
        railway_url (str): URL base de Railway
        intervalo_minutos (int): Intervalo entre consultas
    """
    import time
    from datetime import datetime

    print(f"=== MONITOREO CONTINUO DE LOGS ===")
    print(f"URL: {railway_url}")
    print(f"Intervalo: {intervalo_minutos} minutos")
    print("Presiona Ctrl+C para detener")
    print("=" * 50)

    try:
        while True:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Consultando logs...")

            # Obtener solo logs de la última hora
            logs_response = acceder_logs_via_api(
                railway_url,
                max_lines=10,
                hours_ago=1
            )

            if logs_response:
                logs = logs_response.get('logs', [])
                if logs:
                    print(f"Encontrados {len(logs)} logs recientes")
                    # Mostrar solo el más reciente
                    if logs:
                        log = logs[-1]
                        timestamp = log.get("timestamp", "N/A")[:19]
                        function = log.get("function", log.get("method", "N/A"))
                        success = "✓" if log.get("success") else "✗"
                        print(f"  Más reciente: [{timestamp}] {function} {success}")
                else:
                    print("No hay logs recientes")
            else:
                print("Error al obtener logs")

            time.sleep(intervalo_minutos * 60)

    except KeyboardInterrupt:
        print("\nMonitoreo detenido por el usuario")

def main():
    """Función principal."""
    print("=== ACCESO A LOGS DE TUOTEMPO EN RAILWAY ===")

    # URL de Railway - cambiar por la URL real
    railway_url = os.getenv('RAILWAY_STATIC_URL', 'https://tu-app.railway.app')

    # Si se proporciona una URL como argumento, usarla
    import sys
    if len(sys.argv) > 1:
        railway_url = sys.argv[1]

    print(f"URL de Railway: {railway_url}")

    # Ejemplo 1: Obtener logs recientes
    print("\n1. Obteniendo logs recientes...")
    logs_response = acceder_logs_via_api(railway_url, max_lines=20, hours_ago=2)

    if logs_response:
        imprimir_logs_formateados(logs_response)
        generar_estadisticas_logs(logs_response)
    else:
        print("No se pudieron obtener los logs")
        return

    # Preguntar si quiere monitoreo continuo
    respuesta = input("\n¿Iniciar monitoreo continuo? (y/N): ").lower().strip()
    if respuesta == 'y':
        ejemplo_monitoreo_continuo(railway_url)

if __name__ == "__main__":
    main()
"""
Script para verificar los logs de APIs de tuotempo y analizar errores específicos.
"""

import requests
import json
from datetime import datetime, timedelta

def get_tuotempo_logs(base_url, hours_ago=1):
    """
    Obtiene los logs de las APIs de tuotempo desde Railway.
    """
    try:
        url = f"{base_url}/api/logs/tuotempo"
        params = {
            'max_lines': 100,
            'hours_ago': hours_ago
        }

        print(f"Obteniendo logs desde: {url}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error obteniendo logs: {e}")
        return None

def analyze_reservation_errors(logs_data):
    """
    Analiza los logs buscando errores de reserva específicos.
    """
    if not logs_data or not logs_data.get('success'):
        print("No se pudieron obtener los logs")
        return

    logs = logs_data.get('logs', [])
    print(f"Analizando {len(logs)} entradas de log...")

    reservation_calls = []
    conflict_errors = []

    for log in logs:
        # Buscar llamadas a create_reservation
        if log.get('function') == 'create_reservation':
            reservation_calls.append(log)

        # Buscar llamadas HTTP a endpoints de reserva
        elif log.get('method') == 'POST' and 'reservations' in log.get('endpoint', ''):
            reservation_calls.append(log)

        # Buscar errores de conflicto específicamente
        response = log.get('response') or {}
        if isinstance(response, dict):
            if 'MEMBER_RESERVATION_CONFLICT_ERROR' in str(response):
                conflict_errors.append(log)

    print(f"\n=== ANÁLISIS DE RESERVAS ===")
    print(f"Llamadas a reserva encontradas: {len(reservation_calls)}")
    print(f"Errores de conflicto encontrados: {len(conflict_errors)}")

    # Mostrar llamadas de reserva recientes
    if reservation_calls:
        print(f"\n🔍 ÚLTIMAS LLAMADAS DE RESERVA:")
        for i, call in enumerate(reservation_calls[-5:], 1):  # Últimas 5
            timestamp = call.get('timestamp', 'N/A')[:19]
            success = "✅" if call.get('success') else "❌"
            function = call.get('function', call.get('method', 'N/A'))

            print(f"\n{i}. [{timestamp}] {function} {success}")

            # Mostrar argumentos/parámetros
            args = call.get('args', [])
            kwargs = call.get('kwargs', {})
            payload = call.get('payload', {})

            if args and len(args) > 0:
                print(f"   Args: {args}")
            if kwargs:
                print(f"   Kwargs: {json.dumps(kwargs, indent=2)[:200]}...")
            if payload:
                print(f"   Payload: {json.dumps(payload, indent=2)[:200]}...")

            # Mostrar respuesta
            response = call.get('response', call.get('result'))
            if response:
                response_str = json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
                if len(response_str) > 300:
                    response_str = response_str[:300] + "..."
                print(f"   Respuesta: {response_str}")

            # Mostrar error si hay
            error = call.get('error')
            if error:
                print(f"   ERROR: {error}")

    # Analizar errores de conflicto específicamente
    if conflict_errors:
        print(f"\n🚨 ERRORES DE CONFLICTO DETECTADOS:")
        for i, error in enumerate(conflict_errors, 1):
            timestamp = error.get('timestamp', 'N/A')[:19]
            print(f"\n{i}. [{timestamp}] CONFLICT ERROR")

            response = error.get('response', {})
            if isinstance(response, dict):
                exception = response.get('exception', 'N/A')
                msg = response.get('msg', 'N/A')
                print(f"   Excepción: {exception}")
                print(f"   Mensaje: {msg}")

                # Información de timing
                exec_time = response.get('execution_time')
                if exec_time:
                    print(f"   Tiempo de ejecución: {exec_time}ms")

    return {
        'reservation_calls': len(reservation_calls),
        'conflict_errors': len(conflict_errors),
        'recent_calls': reservation_calls[-3:] if reservation_calls else []
    }

def check_recent_tuotempo_activity(base_url):
    """
    Verifica actividad reciente en las APIs de tuotempo.
    """
    print(f"=== VERIFICACIÓN DE ACTIVIDAD RECIENTE ===")

    # Obtener logs de la última hora
    logs_data = get_tuotempo_logs(base_url, hours_ago=1)
    if not logs_data:
        return

    print(f"Total de logs obtenidos: {logs_data.get('total_logs', 0)}")
    print(f"Parámetros usados: {logs_data.get('parameters', {})}")

    # Analizar errores de reserva
    analysis = analyze_reservation_errors(logs_data)

    # Resumen
    print(f"\n=== RESUMEN ===")
    print(f"- Llamadas de reserva: {analysis['reservation_calls']}")
    print(f"- Errores de conflicto: {analysis['conflict_errors']}")

    if analysis['recent_calls']:
        print(f"- Última actividad: {analysis['recent_calls'][-1].get('timestamp', 'N/A')}")

def main():
    """Función principal"""
    base_url = "https://tuotempo-apis-production.up.railway.app"

    print("=== VERIFICADOR DE LOGS DE ERROR TUOTEMPO ===")
    print("Analizando logs para identificar problemas de reserva...")
    print()

    check_recent_tuotempo_activity(base_url)

if __name__ == "__main__":
    main()
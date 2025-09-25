"""
Script simple para ver logs de tuotempo sin emojis
"""

import requests
import json

def main():
    url = "https://tuotempo-apis-production.up.railway.app/api/logs/tuotempo"
    params = {'max_lines': 20, 'hours_ago': 2}

    print("=== LOGS DE TUOTEMPO APIs ===")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        logs = data.get('logs', [])
        print(f"Total logs: {len(logs)}")
        print(f"Parametros: {data.get('parameters', {})}")
        print("=" * 50)

        # Mostrar logs recientes
        for i, log in enumerate(logs[-10:], 1):  # Últimos 10
            timestamp = log.get('timestamp', 'N/A')[:19]
            function = log.get('function', log.get('method', 'N/A'))
            success = "[OK]" if log.get('success') else "[ERROR]"

            print(f"\n{i}. [{timestamp}] {function} {success}")

            # Mostrar error si hay
            error = log.get('error')
            if error:
                print(f"   ERROR: {error[:100]}...")

            # Mostrar response resumida si es error
            if not log.get('success'):
                response = log.get('response', log.get('result'))
                if isinstance(response, dict):
                    if 'exception' in response:
                        print(f"   Excepcion: {response.get('exception')}")
                    if 'msg' in response:
                        print(f"   Mensaje: {response.get('msg')}")
                elif response:
                    print(f"   Respuesta: {str(response)[:150]}...")

            # Mostrar args si es función
            if log.get('function'):
                args = log.get('args', [])
                kwargs = log.get('kwargs', {})
                if kwargs and 'user_info' in str(kwargs):
                    print(f"   [RESERVA] User: {kwargs}")

        # Buscar específicamente errores de conflicto
        print(f"\n{'='*50}")
        print("ERRORES DE CONFLICTO:")
        conflict_found = False

        for log in logs:
            response = log.get('response', {})
            if isinstance(response, dict) and 'MEMBER_RESERVATION_CONFLICT_ERROR' in str(response):
                conflict_found = True
                timestamp = log.get('timestamp', 'N/A')[:19]
                print(f"\n[{timestamp}] CONFLICT ERROR encontrado:")
                print(f"  Excepcion: {response.get('exception', 'N/A')}")
                print(f"  Mensaje: {response.get('msg', 'N/A')}")
                print(f"  Tiempo exec: {response.get('execution_time', 'N/A')}ms")

                # Mostrar detalles del error
                details = response.get('details', {})
                if details:
                    print(f"  Detalles adicionales:")
                    for key, value in details.items():
                        if key in ['debug', 'net_execution_time', 'providers_requests']:
                            print(f"    {key}: {value}")

        if not conflict_found:
            print("  No se encontraron errores de conflicto en estos logs")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
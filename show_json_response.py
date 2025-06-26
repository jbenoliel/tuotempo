import json
import requests
import sys
from tuotempo_api import TuoTempoAPI
from datetime import datetime

def print_json(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2, ensure_ascii=False))
    sys.stdout.flush()  # Asegurar que la salida se muestre inmediatamente

def debug_request(url, method, headers, params=None, data=None):
    """Print request details for debugging"""
    print(f"\n--- DEBUG: {method} {url} ---")
    print(f"Headers: {headers}")
    if params:
        print(f"Params: {params}")
    if data:
        print(f"Data: {data}")
    print("---")
    sys.stdout.flush()

def main():
    # Initialize the TuoTempo API client
    api = TuoTempoAPI(
        lang="es",  # Use Spanish language
        environment="PRE"  # Use PRE environment
    )
    
    # Patch the requests methods to print debug info
    original_get = requests.get
    
    def debug_get(*args, **kwargs):
        debug_request(args[0], "GET", kwargs.get('headers', {}), kwargs.get('params', {}))
        response = original_get(*args, **kwargs)
        print(f"Response status code: {response.status_code}")
        sys.stdout.flush()
        return response
    
    # Reemplazar temporalmente los métodos de requests para depuración
    requests.get = debug_get
    
    # Usar un centro específico
    area_id = "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh"  # Adeslas Dental Badalona
    
    # Usar ID de actividad para primera visita a odontología general
    activity_id = "sc159232371eb9c1"
    
    # Usar la fecha actual en formato DD/MM/YYYY
    today = datetime.now()
    start_date = today.strftime("%d/%m/%Y")
    
    print(f"Consultando disponibilidad para el centro: Adeslas Dental Badalona")
    print(f"Fecha: {start_date}")
    print(f"ID de actividad: {activity_id}")
    
    # Hacer la llamada a la API
    slots_response = api.get_available_slots(
        activity_id=activity_id,
        area_id=area_id,
        start_date=start_date
    )
    
    # Mostrar la respuesta completa en formato JSON
    print("\nRespuesta JSON completa:")
    print_json(slots_response)
    sys.stdout.flush()
    
    # Mostrar la estructura de la respuesta
    if slots_response.get("result") == "OK":
        print("\nEstructura de la respuesta:")
        print("- result: Indica si la llamada fue exitosa ('OK' o 'KO')")
        print("- return: Contiene los resultados de la llamada")
        print("  - results: Contiene los datos principales")
        print("    - availabilities: Lista de slots disponibles")
        sys.stdout.flush()
        
        # Mostrar un ejemplo de slot si hay disponibles
        availabilities = slots_response.get("return", {}).get("results", {}).get("availabilities", [])
        if availabilities:
            print("\nEjemplo de un slot disponible:")
            print_json(availabilities[0])
        else:
            print("\nNo hay slots disponibles para la fecha seleccionada.")
    else:
        print("\nError en la llamada a la API:")
        print_json(api.handle_error(slots_response))
    
    # Restaurar los métodos originales de requests
    requests.get = original_get

if __name__ == "__main__":
    main()

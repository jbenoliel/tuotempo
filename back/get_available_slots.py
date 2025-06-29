import json
import requests
from tuotempo_api import TuoTempoAPI
from datetime import datetime, timedelta

def print_json(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def debug_request(url, method, headers, params=None, data=None):
    """Print request details for debugging"""
    print(f"\n--- DEBUG: {method} {url} ---")
    print(f"Headers: {headers}")
    if params:
        print(f"Params: {params}")
    if data:
        print(f"Data: {data}")
    print("---")

def main():
    # Initialize the TuoTempo API client
    api = TuoTempoAPI(
        lang="es",  # Use Spanish language
        environment="PRE"  # Use PRE environment
    )
    
    # Patch the requests methods to print debug info
    original_get = requests.get
    original_post = requests.post
    
    def debug_get(*args, **kwargs):
        debug_request(args[0], "GET", kwargs.get('headers', {}), kwargs.get('params', {}))
        response = original_get(*args, **kwargs)
        print(f"Response status code: {response.status_code}")
        return response
        
    def debug_post(*args, **kwargs):
        debug_request(args[0], "POST", kwargs.get('headers', {}), kwargs.get('params', {}), kwargs.get('json', {}))
        response = original_post(*args, **kwargs)
        print(f"Response status code: {response.status_code}")
        return response
    
    # Reemplazar temporalmente los métodos de requests para depuración
    requests.get = debug_get
    requests.post = debug_post
    
    # Primero obtenemos la lista de centros disponibles
    print("Obteniendo lista de centros disponibles...")
    centers_response = api.get_centers()
    
    if centers_response.get("result") != "OK":
        print("Error al obtener centros:")
        print_json(api.handle_error(centers_response))
        return
    
    # Mostrar los centros disponibles
    centers = centers_response.get('return', {}).get('results', [])
    print(f"\nSe encontraron {len(centers)} centros:")
    
    for i, center in enumerate(centers[:10], 1):  # Mostrar solo los primeros 10 centros
        print(f"{i}. ID: {center.get('areaid')} - {center.get('areaTitle')} ({center.get('province')})")
    
    if len(centers) > 10:
        print(f"... y {len(centers) - 10} centros más")
    
    # Seleccionar el primer centro para la demostración
    if not centers:
        print("No se encontraron centros disponibles.")
        return
    
    selected_center = centers[0]
    area_id = selected_center.get("areaid")
    
    # Usar ID de actividad para primera visita a odontología general
    activity_id = "sc159232371eb9c1"
    
    # Obtener fechas para los próximos 30 días
    today = datetime.now()
    
    print(f"\nBuscando slots disponibles para el centro: {selected_center.get('areaTitle')}")
    print(f"ID del centro: {area_id}")
    print(f"Actividad: {activity_id} (primera visita odontología general)")
    print("Consultando disponibilidad para los próximos 7 días:")
    
    # Consultar disponibilidad para los próximos 7 días (reducido de 30 para evitar demasiadas llamadas API)
    for i in range(3):  # Reducido a 3 días para limitar el número de llamadas API
        date = today + timedelta(days=i)
        start_date = date.strftime("%d/%m/%Y")
        
        print(f"\nConsultando disponibilidad para: {start_date}")
        slots_response = api.get_available_slots(
            activity_id=activity_id,
            area_id=area_id,
            start_date=start_date
        )
        
        # Mostrar la respuesta completa para depuración
        print("\nRespuesta completa:")
        print_json(slots_response)
        
        if slots_response.get("result") != "OK":
            print(f"Error al obtener slots para {start_date}:")
            print_json(api.handle_error(slots_response))
            continue
        
        availabilities = slots_response.get("return", {}).get("results", {}).get("availabilities", [])
        if availabilities:
            print(f"✅ Encontrados {len(availabilities)} slots disponibles para {start_date}:")
            for slot in availabilities[:5]:  # Mostrar solo los primeros 5 slots para no saturar la salida
                print(f"  - {slot.get('start_date')} a las {slot.get('startTime')} con {slot.get('resourceName')}")
            
            if len(availabilities) > 5:
                print(f"  ... y {len(availabilities) - 5} slots más")
        else:
            print(f"❌ No hay slots disponibles para {start_date}")
    
    # Restaurar los métodos originales de requests
    requests.get = original_get
    requests.post = original_post

if __name__ == "__main__":
    main()

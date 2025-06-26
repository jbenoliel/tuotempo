import json
import requests
from tuotempo_api import TuoTempoAPI
from datetime import datetime

def main():
    # Initialize the TuoTempo API client
    api = TuoTempoAPI(
        lang="es",  # Use Spanish language
        environment="PRE"  # Use PRE environment
    )
    
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
    
    # Guardar la respuesta en un archivo JSON
    with open('api_response.json', 'w', encoding='utf-8') as f:
        json.dump(slots_response, f, indent=2, ensure_ascii=False)
    
    print("\nLa respuesta completa se ha guardado en el archivo 'api_response.json'")
    
    # Mostrar información básica sobre la respuesta
    if slots_response.get("result") == "OK":
        availabilities = slots_response.get("return", {}).get("results", {}).get("availabilities", [])
        print(f"\nSe encontraron {len(availabilities)} slots disponibles")
        
        if availabilities:
            print("\nEjemplo de campos en un slot disponible:")
            slot = availabilities[0]
            for key in slot.keys():
                print(f"- {key}")
    else:
        print("\nError en la llamada a la API")

if __name__ == "__main__":
    main()

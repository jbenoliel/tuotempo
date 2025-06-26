import json
from tuotempo_api import TuoTempoAPI
from datetime import datetime

def main():
    # Inicializar el cliente de API
    api = TuoTempoAPI(
        lang="es",
        environment="PRE"  # Usar entorno PRE
    )
    
    # Usar un centro específico
    area_id = "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh"  # Adeslas Dental Badalona
    
    # Usar ID de actividad para primera visita a odontología general
    activity_id = "sc159232371eb9c1"
    
    # Usar una fecha futura fija para asegurar que hay slots disponibles
    start_date = "01/07/2025"  # 1 de julio de 2025
    
    print(f"Consultando disponibilidad para el centro: Adeslas Dental Badalona")
    print(f"Fecha: {start_date}")
    print(f"ID de actividad: {activity_id}")
    
    # Hacer la llamada a la API
    slots_response = api.get_available_slots(
        activity_id=activity_id,
        area_id=area_id,
        start_date=start_date
    )
    
    # Guardar la respuesta en un archivo
    with open('slots_response.json', 'w', encoding='utf-8') as f:
        json.dump(slots_response, f, indent=2, ensure_ascii=False)
    
    print("\nLa respuesta completa se ha guardado en el archivo 'slots_response.json'")
    
    # Mostrar la estructura básica de la respuesta
    if slots_response.get("result") == "OK":
        print("\nEstructura básica de la respuesta:")
        print("- result:", slots_response.get("result"))
        
        return_data = slots_response.get("return", {})
        results = return_data.get("results", {})
        availabilities = results.get("availabilities", [])
        
        print(f"- return: contiene los resultados")
        print(f"  - results: contiene los datos principales")
        print(f"    - availabilities: lista con {len(availabilities)} slots disponibles")
        
        if availabilities:
            # Mostrar un ejemplo simplificado de un slot
            slot = availabilities[0]
            print("\nEjemplo de un slot disponible (campos principales):")
            important_fields = [
                "start_date", "startTime", "endTime", 
                "resourceName", "areaTitle", "activityTitle",
                "provider_session_id"
            ]
            
            for field in important_fields:
                if field in slot:
                    print(f"- {field}: {slot[field]}")
    else:
        print("\nError en la respuesta:")
        print(f"- result: {slots_response.get('result')}")
        if "error" in slots_response:
            print(f"- error: {slots_response.get('error')}")

if __name__ == "__main__":
    main()

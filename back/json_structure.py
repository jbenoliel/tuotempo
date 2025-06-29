import json
from tuotempo_api import TuoTempoAPI

def main():
    # Inicializar el cliente de API
    api = TuoTempoAPI(
        lang="es",
        environment="PRE"
    )
    
    # Parámetros fijos para asegurar una respuesta consistente
    area_id = "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh"  # Adeslas Dental Badalona
    activity_id = "sc159232371eb9c1"  # Primera Visita
    start_date = "01/07/2025"  # Fecha fija en el futuro
    
    # Hacer la llamada a la API
    response = api.get_available_slots(
        activity_id=activity_id,
        area_id=area_id,
        start_date=start_date
    )
    
    # Guardar la respuesta completa en un archivo
    with open('slots_full_response.json', 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=2, ensure_ascii=False)
    
    print("Respuesta JSON completa guardada en 'slots_full_response.json'")
    
    # Crear una versión simplificada de la respuesta para mostrar
    simplified = {
        "result": response.get("result")
    }
    
    if response.get("result") == "OK":
        availabilities = response.get("return", {}).get("results", {}).get("availabilities", [])
        
        # Incluir solo el primer slot disponible (si existe) con campos seleccionados
        if availabilities:
            slot = availabilities[0]
            simplified["example_slot"] = {
                "start_date": slot.get("start_date"),
                "startTime": slot.get("startTime"),
                "endTime": slot.get("endTime"),
                "resourceName": slot.get("resourceName"),
                "areaTitle": slot.get("areaTitle"),
                "activityTitle": slot.get("activityTitle"),
                "provider_session_id": slot.get("provider_session_id")
            }
            simplified["total_slots"] = len(availabilities)
    
    # Mostrar la versión simplificada
    print("\nEstructura básica de la respuesta:")
    print(json.dumps(simplified, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

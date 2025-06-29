import json
import os
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
    
    # Guardar la respuesta JSON completa en un archivo
    output_file = "available_slots_response.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(slots_response, f, indent=2, ensure_ascii=False)
    
    print(f"\nRespuesta JSON completa guardada en el archivo: {output_file}")
    
    # Mostrar información sobre la estructura
    print("\n--- Estructura de la respuesta ---")
    print("result:", slots_response.get("result"))
    
    if slots_response.get("result") == "OK":
        availabilities = slots_response.get("return", {}).get("results", {}).get("availabilities", [])
        print(f"Número de slots disponibles: {len(availabilities)}")
        
        if availabilities:
            print("\nCampos principales de un slot disponible:")
            important_fields = ["start_date", "startTime", "endTime", "resourceName", "areaTitle", 
                              "activityTitle", "provider_session_id"]
            
            print("\nEjemplo de un slot disponible (campos principales):")
            for field in important_fields:
                if field in availabilities[0]:
                    print(f"- {field}: {availabilities[0][field]}")
                    
            print("\nPara ver todos los campos y valores, revisa el archivo JSON generado.")
        else:
            print("\nNo hay slots disponibles para la fecha seleccionada.")
    else:
        print("\nError en la llamada a la API:")
        print(json.dumps(slots_response, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

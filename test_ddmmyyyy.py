import json
import requests

def main():
    # URL y headers
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities"
    
    # Parámetros de la consulta con formato de fecha DD/MM/YYYY
    params = {
        "lang": "es",
        "activityid": "sc159232371eb9c1",
        "areaId": "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh",
        "start_date": "25/06/2025",
        "bypass_availabilities_fallback": "true"
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    print(f"Ejecutando petición con fecha en formato DD/MM/YYYY: {params['start_date']}")
    
    # Realizar la llamada HTTP
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            json_response = response.json()
            
            # Guardar la respuesta completa en un archivo
            with open('response_ddmmyyyy.json', 'w', encoding='utf-8') as f:
                json.dump(json_response, f, indent=2, ensure_ascii=False)
            
            print(f"Código de estado: {response.status_code}")
            print(f"Respuesta guardada en 'response_ddmmyyyy.json'")
            
            # Analizar la respuesta
            if json_response.get("result") == "OK":
                availabilities = json_response.get("return", {}).get("results", {}).get("availabilities", [])
                print(f"Resultado: {json_response.get('result')}")
                print(f"Slots disponibles: {len(availabilities)}")
                
                if availabilities:
                    # Extraer valores únicos de start_date
                    start_dates = set()
                    for slot in availabilities:
                        start_dates.add(slot.get("start_date"))
                    
                    print(f"\nValores únicos de start_date ({len(start_dates)}):")
                    for date in sorted(start_dates):
                        print(f"  - {date}")
                    
                    # Mostrar el primer slot
                    print("\nPrimer slot disponible:")
                    slot = availabilities[0]
                    print(f"- Fecha: {slot.get('start_date')}")
                    print(f"- Hora: {slot.get('startTime')}")
                    print(f"- Profesional: {slot.get('resourceName')}")
                else:
                    print("No se encontraron slots disponibles")
            else:
                print(f"Error en la respuesta: {json_response.get('msg', 'No hay mensaje de error')}")
        else:
            print(f"Error en la llamada: Código de estado {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"Error al realizar la llamada: {e}")

if __name__ == "__main__":
    main()

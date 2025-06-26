import json
import requests

def print_json(data):
    """Imprime datos JSON con formato legible"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def main():
    # URL y headers según el request proporcionado
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities"
    
    # Parámetros de la consulta con formato de fecha YYYY-MM-DD
    params = {
        "lang": "es",
        "activityid": "sc159232371eb9c1",
        "areaId": "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh",
        "start_date": "2025-06-25",
        "bypass_availabilities_fallback": "true"
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    print(f"Ejecutando petición con fecha en formato YYYY-MM-DD: {params['start_date']}")
    
    # Realizar la llamada HTTP
    try:
        response = requests.get(url, headers=headers, params=params)
        
        # Verificar si la llamada fue exitosa
        if response.status_code == 200:
            # Convertir la respuesta a JSON
            json_response = response.json()
            
            # Guardar la respuesta completa en un archivo
            with open('curl_ymd_response.json', 'w', encoding='utf-8') as f:
                json.dump(json_response, f, indent=2, ensure_ascii=False)
            
            print(f"Código de estado: {response.status_code}")
            print(f"Respuesta completa guardada en 'curl_ymd_response.json'\n")
            
            # Mostrar información básica de la respuesta
            if json_response.get("result") == "OK":
                availabilities = json_response.get("return", {}).get("results", {}).get("availabilities", [])
                print(f"Resultado: {json_response.get('result')}")
                print(f"Slots disponibles: {len(availabilities)}")
                
                if availabilities:
                    print("\nEjemplo de un slot disponible:")
                    slot = availabilities[0]
                    important_fields = [
                        "start_date", "startTime", "endTime", "resourceName", 
                        "areaTitle", "activityTitle", "provider_session_id"
                    ]
                    for field in important_fields:
                        if field in slot:
                            print(f"- {field}: {slot[field]}")
                else:
                    print("No se encontraron slots disponibles")
            else:
                print("Error en la respuesta:")
                print_json(json_response)
        else:
            print(f"Error en la llamada: Código de estado {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"Error al realizar la llamada: {e}")

if __name__ == "__main__":
    main()

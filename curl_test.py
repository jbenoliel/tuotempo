import json
import requests
import urllib.parse
from datetime import datetime

def print_json(data):
    """Imprime datos JSON con formato legible"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def main():
    # Parámetros de la API
    base_url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities"
    
    # Headers
    headers = {
        "content-type": "application/json; charset=UTF-8"
    }
    
    # Fecha actual en formato DD/MM/YYYY
    today = datetime.now()
    fecha_deseada = today.strftime("%d/%m/%Y")
    
    # Parámetros de la consulta
    params = {
        "lang": "es",
        "activityid": "sc159232371eb9c1",
        "areaId": "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh",
        "start_date": fecha_deseada,
        "bypass_availabilities_fallback": "true"
    }
    
    # Construir la URL con los parámetros
    query_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
    full_url = f"{base_url}?{query_string}"
    
    # Guardar el comando curl en un archivo para referencia
    curl_command = f"curl -X GET -H \"content-type: application/json; charset=UTF-8\" \"{full_url}\""
    with open('curl_command.txt', 'w', encoding='utf-8') as f:
        f.write(curl_command)
    
    print("Comando curl guardado en 'curl_command.txt'")
    print("Ejecutando llamada...")

    
    # Realizar la llamada HTTP
    try:
        response = requests.get(base_url, headers=headers, params=params)
        
        # Verificar si la llamada fue exitosa
        if response.status_code == 200:
            # Convertir la respuesta a JSON
            json_response = response.json()
            
            # Guardar la respuesta completa en un archivo
            with open('curl_response.json', 'w', encoding='utf-8') as f:
                json.dump(json_response, f, indent=2, ensure_ascii=False)
            
            print(f"Código de estado: {response.status_code}")
            print(f"Respuesta completa guardada en 'curl_response.json'\n")
            
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
                print("Error en la respuesta:")
                print_json(json_response)
        else:
            print(f"Error en la llamada: Código de estado {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"Error al realizar la llamada: {e}")

if __name__ == "__main__":
    main()

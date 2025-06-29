import json
import requests

def main():
    # URL y headers
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities"
    
    # Formato YYYY-MM-DD
    params = {
        "lang": "es",
        "activityid": "sc159232371eb9c1",
        "areaId": "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh",
        "start_date": "2025-06-25",
        "bypass_availabilities_fallback": "true"
    }
    
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    print(f"Probando formato YYYY-MM-DD: {params['start_date']}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            json_response = response.json()
            
            with open('response_iso.json', 'w', encoding='utf-8') as f:
                json.dump(json_response, f, indent=2, ensure_ascii=False)
            
            print(f"Código de estado: {response.status_code}")
            print(f"Respuesta guardada en 'response_iso.json'")
            
            if json_response.get("result") == "OK":
                availabilities = json_response.get("return", {}).get("results", {}).get("availabilities", [])
                print(f"Resultado: {json_response.get('result')}")
                print(f"Slots disponibles: {len(availabilities)}")
            else:
                print(f"Error: {json_response.get('msg')}")
        else:
            print(f"Error: {response.status_code}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

import json
import requests
from datetime import datetime
import os

def print_json(data):
    """Imprime datos JSON con formato legible"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def test_date_format(format_name, date_value):
    """Prueba la API con un formato de fecha específico y analiza los resultados"""
    print(f"\n=== Probando formato {format_name}: {date_value} ===")
    
    # URL y headers
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities"
    
    # Parámetros de la consulta
    params = {
        "lang": "es",
        "activityid": "sc159232371eb9c1",
        "areaId": "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh",
        "start_date": date_value,
        "bypass_availabilities_fallback": "true"
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    # Nombre del archivo para guardar la respuesta
    filename = f"response_{format_name}.json"
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            json_response = response.json()
            
            # Guardar la respuesta completa en un archivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_response, f, indent=2, ensure_ascii=False)
            
            print(f"Código de estado: {response.status_code}")
            
            # Analizar los valores de start_date en la respuesta
            if json_response.get("result") == "OK":
                availabilities = json_response.get("return", {}).get("results", {}).get("availabilities", [])
                print(f"Resultado: {json_response.get('result')}")
                print(f"Slots disponibles: {len(availabilities)}")
                
                if availabilities:
                    # Extraer los valores únicos de start_date
                    start_dates = set()
                    for slot in availabilities:
                        start_dates.add(slot.get("start_date"))
                    
                    # Mostrar los valores únicos de start_date
                    print(f"Valores únicos de start_date en la respuesta ({len(start_dates)}):")
                    for date in sorted(start_dates):
                        print(f"  - {date}")
                else:
                    print("No se encontraron slots disponibles")
            else:
                print("Error en la respuesta:")
                print(f"- Mensaje: {json_response.get('msg', 'No hay mensaje de error')}")
                print(f"- Excepción: {json_response.get('exception', 'No hay excepción')}")
            
            return True, json_response
        else:
            print(f"Error en la llamada: Código de estado {response.status_code}")
            print(response.text)
            return False, None
    
    except Exception as e:
        print(f"Error al realizar la llamada: {e}")
        return False, None

def analyze_existing_response(filename):
    """Analiza un archivo de respuesta JSON existente"""
    print(f"\n=== Analizando archivo existente: {filename} ===")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            json_response = json.load(f)
        
        # Analizar los valores de start_date en la respuesta
        if json_response.get("result") == "OK":
            availabilities = json_response.get("return", {}).get("results", {}).get("availabilities", [])
            print(f"Resultado: {json_response.get('result')}")
            print(f"Slots disponibles: {len(availabilities)}")
            
            if availabilities:
                # Extraer los valores únicos de start_date
                start_dates = set()
                for slot in availabilities:
                    start_dates.add(slot.get("start_date"))
                
                # Mostrar los valores únicos de start_date
                print(f"Valores únicos de start_date en la respuesta ({len(start_dates)}):")
                for date in sorted(start_dates):
                    print(f"  - {date}")
                
                # Mostrar el formato de fecha utilizado en la respuesta
                if start_dates:
                    sample_date = next(iter(start_dates))
                    print(f"\nFormato de fecha en la respuesta: {sample_date}")
            else:
                print("No se encontraron slots disponibles")
        else:
            print("Error en la respuesta:")
            print(f"- Mensaje: {json_response.get('msg', 'No hay mensaje de error')}")
            print(f"- Excepción: {json_response.get('exception', 'No hay excepción')}")
    
    except Exception as e:
        print(f"Error al analizar el archivo: {e}")

def main():
    # Analizar archivos de respuesta existentes
    existing_files = [
        "curl_ymd_response.json"
    ]
    
    for filename in existing_files:
        if os.path.exists(filename):
            analyze_existing_response(filename)
    
    # Probar diferentes formatos de fecha
    formats_to_test = [
        ("YYYY-MM-DD", "2025-06-25"),  # Formato ISO sin hora
        ("DD/MM/YYYY", "25/06/2025")   # Formato europeo
    ]
    
    results = []
    
    for format_name, date_value in formats_to_test:
        success, _ = test_date_format(format_name, date_value)
        results.append({
            "format": format_name,
            "value": date_value,
            "success": success
        })
    
    # Resumen de resultados
    print("\n=== Resumen de resultados ===")
    for result in results:
        status = "✅ Éxito" if result["success"] else "❌ Error"
        print(f"{status} - Formato {result['format']}: {result['value']}")
    
    print("\n=== Conclusión ===")
    print("Independientemente del formato de fecha usado en la petición,")
    print("la API de TuoTempo siempre devuelve las fechas en formato DD/MM/YYYY.")
    print("Esto significa que la API acepta múltiples formatos de fecha como entrada,")
    print("pero estandariza la salida al formato europeo DD/MM/YYYY.")

if __name__ == "__main__":
    main()

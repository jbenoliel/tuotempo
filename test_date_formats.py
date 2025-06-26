import json
import requests
import os
from datetime import datetime

def print_json(data):
    """Imprime datos JSON con formato legible"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def test_date_format(date_format, date_value):
    """Prueba la API con un formato de fecha específico"""
    print(f"\n=== Probando formato de fecha: {date_format} (valor: {date_value}) ===")
    
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
    filename = f"response_{date_format}.json"
    
    # Realizar la llamada HTTP
    try:
        response = requests.get(url, headers=headers, params=params)
        
        # Verificar si la llamada fue exitosa
        if response.status_code == 200:
            # Convertir la respuesta a JSON
            json_response = response.json()
            
            # Guardar la respuesta completa en un archivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_response, f, indent=2, ensure_ascii=False)
            
            print(f"Código de estado: {response.status_code}")
            print(f"Respuesta guardada en '{filename}'")
            
            # Mostrar información básica de la respuesta
            if json_response.get("result") == "OK":
                availabilities = json_response.get("return", {}).get("results", {}).get("availabilities", [])
                print(f"Resultado: {json_response.get('result')}")
                print(f"Slots disponibles: {len(availabilities)}")
                
                if availabilities:
                    print("Primer slot disponible:")
                    slot = availabilities[0]
                    print(f"- Fecha: {slot.get('start_date')}")
                    print(f"- Hora: {slot.get('startTime')}")
                else:
                    print("No se encontraron slots disponibles")
            else:
                print("Error en la respuesta:")
                print(f"- Mensaje: {json_response.get('msg', 'No hay mensaje de error')}")
                print(f"- Excepción: {json_response.get('exception', 'No hay excepción')}")
        else:
            print(f"Error en la llamada: Código de estado {response.status_code}")
            print(response.text)
        
        return True
    
    except Exception as e:
        print(f"Error al realizar la llamada: {e}")
        return False

def main():
    # Probar diferentes formatos de fecha
    formats_to_test = [
        ("YYYY-MM-DD", "2025-06-25"),  # Formato ISO sin hora
        ("DD/MM/YYYY", "25/06/2025"),  # Formato europeo
        ("MM/DD/YYYY", "06/25/2025")   # Formato americano
    ]
    
    results = []
    
    for date_format, date_value in formats_to_test:
        success = test_date_format(date_format, date_value)
        results.append({
            "format": date_format,
            "value": date_value,
            "success": success
        })
    
    # Resumen de resultados
    print("\n=== Resumen de resultados ===")
    for result in results:
        status = "✅ Éxito" if result["success"] else "❌ Error"
        print(f"{status} - Formato {result['format']}: {result['value']}")

if __name__ == "__main__":
    main()

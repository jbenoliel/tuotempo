import json
import os

def analyze_json_file(filename):
    """Analiza un archivo JSON existente para extraer los valores de start_date"""
    print(f"Analizando archivo: {filename}")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get("result") == "OK":
            availabilities = data.get("return", {}).get("results", {}).get("availabilities", [])
            print(f"Total de slots disponibles: {len(availabilities)}")
            
            if availabilities:
                # Extraer valores únicos de start_date
                start_dates = set()
                for slot in availabilities:
                    start_dates.add(slot.get("start_date"))
                
                print(f"\nValores únicos de start_date ({len(start_dates)}):")
                for date in sorted(start_dates):
                    print(f"  - {date}")
                
                # Mostrar el primer slot completo como ejemplo
                print("\nEjemplo de un slot completo:")
                first_slot = availabilities[0]
                print(json.dumps(first_slot, indent=2, ensure_ascii=False))
            else:
                print("No se encontraron slots disponibles en la respuesta")
        else:
            print(f"Error en la respuesta: {data.get('msg', 'No hay mensaje de error')}")
    
    except Exception as e:
        print(f"Error al analizar el archivo: {e}")

def main():
    # Archivo a analizar
    filename = "curl_ymd_response.json"
    
    if os.path.exists(filename):
        analyze_json_file(filename)
    else:
        print(f"El archivo {filename} no existe")

if __name__ == "__main__":
    main()

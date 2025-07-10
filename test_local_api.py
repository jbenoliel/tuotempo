import requests
import json

def test_reservar_api_local():
    """Prueba el endpoint /api/reservar en el servidor local."""
    url = "http://127.0.0.1:5000/api/reservar"
    
    # Datos de ejemplo para la reserva. 
    # Puedes cambiar el 'member_id' a uno que exista en tu base de datos de prueba.
    payload = {
        "member_id": "12345",
        "resource_id": "some_resource_id",
        "location_id": "some_location_id",
        "comments": "Esto es una prueba desde el script local."
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print(f"Enviando petición POST a: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\n--- Respuesta del Servidor ---")
        print(f"Código de Estado: {response.status_code}")
        
        # Intentar decodificar la respuesta JSON
        try:
            response_json = response.json()
            print("Respuesta (JSON):")
            print(json.dumps(response_json, indent=2))
        except json.JSONDecodeError:
            print("Respuesta (texto plano):")
            print(response.text)
            
        return response.status_code, response.text
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n[ERROR] No se pudo conectar al servidor en {url}.")
        print("Asegúrate de que estás ejecutando 'python api_tuotempo.py' en otra terminal.")
        return None, str(e)
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error inesperado: {e}")
        return None, str(e)

if __name__ == "__main__":
    test_reservar_api_local()

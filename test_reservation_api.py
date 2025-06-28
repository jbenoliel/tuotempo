import requests
import json
import time

def test_reservation_api(include_end_time=False):
    """Prueba la API de reservas de TuoTempo con o sin el campo endTime"""
    
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/reservations"
    
    # Fecha de ejemplo para la cita (mañana a las 10:00)
    start_time = "2025-07-01 10:00"
    
    # Payload base
    payload = {
        "userid": "sc16859596caff25",
        "Communication_phone": "670252676",
        "Tags": "WEB_NO_ASEGURADO",
        "startTime": start_time,
        "resourceid": "sc12345678",  # Reemplazar con un ID de recurso válido
        "activityid": "sc159232371eb9c1",
        "isExternalPayment": "false"
    }
    
    # Añadir endTime solo si se solicita
    if include_end_time:
        payload["endTime"] = "2025-07-01 10:30"  # 30 minutos después
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 24b98d8d41b970d38362b52bd3505c04',
        'Cookie': 'lang=es'
    }
    
    print(f"\n{'='*50}")
    print(f"PRUEBA {'CON' if include_end_time else 'SIN'} endTime")
    print(f"{'='*50}")
    
    print(f"\nJSON enviado:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\nCódigo de estado: {response.status_code}")
        print(f"Respuesta en texto plano:")
        print(response.text)
        
        # Intentar parsear la respuesta como JSON
        try:
            json_response = response.json()
            print(f"\nRespuesta JSON formateada:")
            print(json.dumps(json_response, indent=2))
            
            # Analizar el resultado
            if "result" in json_response:
                if json_response["result"] == "OK":
                    print("\n✅ La solicitud fue exitosa")
                else:
                    print(f"\n❌ La solicitud falló: {json_response.get('msg', 'Sin mensaje')}")
            
        except json.JSONDecodeError:
            print("\n❌ La respuesta no es un JSON válido")
            
    except Exception as e:
        print(f"\n❌ Error al realizar la solicitud: {e}")

# Ejecutar pruebas
if __name__ == "__main__":
    print("PRUEBA DE API DE RESERVAS TUOTEMPO")
    print("==================================")
    
    # Primero sin endTime
    test_reservation_api(include_end_time=False)
    
    # Esperar un poco entre solicitudes
    time.sleep(2)
    
    # Luego con endTime
    test_reservation_api(include_end_time=True)

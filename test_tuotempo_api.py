import requests
import json

url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/users"

# Payload corregido
payload = {
    "fname": "Raul",
    "lname": "Valo",
    "privacy": 1,           # Número en lugar de string con comillas
    "phone": "999555444",
    "Onetime_user": 1,      # Número en lugar de string con comillas
    "birthday": "25/02/1976"
}

headers = {
    'Content-Type': 'application/json',
    'Cookie': 'lang=es'
}

try:
    print("Enviando solicitud a TuoTempo API...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Código de estado: {response.status_code}")
    print(f"Respuesta: {response.text}")
    
    # Intentar parsear la respuesta como JSON
    try:
        json_response = response.json()
        print(f"Respuesta JSON: {json.dumps(json_response, indent=2)}")
    except:
        print("La respuesta no es un JSON válido")
        
except Exception as e:
    print(f"Error al realizar la solicitud: {e}")

# También probar con una variante alternativa del formato de fecha
print("\n--- Probando con formato de fecha alternativo ---\n")

payload["birthday"] = "1976-02-25"  # Formato ISO YYYY-MM-DD

try:
    print(f"Payload alternativo: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Código de estado: {response.status_code}")
    print(f"Respuesta: {response.text}")
    
except Exception as e:
    print(f"Error al realizar la solicitud: {e}")

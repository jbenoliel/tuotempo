"""
Test directo con los datos de MANUEL PANPLONA NAVARRO
"""

import requests
import json

def test_api_manuel():
    url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Datos exactos que proporcionaste
    data = {
        "codigoPostal": "8226",
        "delegacion": "81", 
        "dias_tardes": "Buenos días",
        "fechaNacimiento": "19811220",
        "firstName": "MANUEL",
        "lastName": "PANPLONA NAVARRO",
        "phoneNumber": "+34613750493",
        "sexo": "VARÓN",
        "agentName": "Ana Martín",
        "fechaDeseada": "23-09-2025",
        "preferenciaMT": "morning",
        "interesado": "interesado",
        "sr_sra": "señor",
        "callResult": "Cita agendada",
        "telefono": "613750493"
    }
    
    print("PROBANDO API CON DATOS DE MANUEL PANPLONA NAVARRO")
    print("="*60)
    print("Datos enviados:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        print(f"\nRespuesta:")
        print(f"Status: {response.status_code}")
        print(f"Texto: {response.text}")
        
        if response.status_code == 200:
            print("\nAPI respondio OK - Verificando en BD...")
            return True
        else:
            print(f"\nError en API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_api_manuel()
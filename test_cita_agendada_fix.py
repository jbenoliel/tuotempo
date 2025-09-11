"""
Test para verificar que el fix de detección de citas funciona
"""

import requests
import json

def test_cita_agendada_fix():
    """
    Prueba el endpoint con el ejemplo proporcionado por el usuario
    """
    
    # URL del endpoint
    url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Ejemplo proporcionado por el usuario
    test_data = {
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
        "telefono": "613750493"  # También incluir el campo telefono normalizado
    }
    
    print("PROBANDO FIX DE DETECCIÓN DE CITAS")
    print("="*50)
    print(f"URL: {url}")
    print(f"Datos de prueba:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print()
    
    try:
        # Hacer la petición POST
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS - La petición fue exitosa")
            try:
                response_json = response.json()
                print("Respuesta JSON:")
                print(json.dumps(response_json, indent=2, ensure_ascii=False))
                
                # Verificar si se detectó la cita
                if 'success' in response_json and response_json['success']:
                    print("\n✅ El lead debería estar marcado como 'Cita Agendada' con 'Con Pack'")
                else:
                    print("\n⚠️ La respuesta no indica éxito completo")
                    
            except ValueError:
                print("Respuesta no es JSON válido:")
                print(response.text)
        else:
            print(f"❌ ERROR - Status code: {response.status_code}")
            print("Response text:")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la petición: {e}")
    
    print("\n" + "="*50)
    print("VERIFICACIÓN EN BASE DE DATOS")
    print("Deberías verificar manualmente que el lead MANUEL PANPLONA NAVARRO")
    print("con teléfono 613750493 tenga:")
    print("  - status_level_1: 'Cita Agendada'")
    print("  - status_level_2: 'Con Pack'")

if __name__ == "__main__":
    test_cita_agendada_fix()
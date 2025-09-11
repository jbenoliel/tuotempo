"""
Test con un lead real para verificar Sin Pack vs Con Pack
"""

import requests
import json

def test_lead_real():
    url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Usar MIGUEL ARTURO HINOJOSA HICIANO que aparecía en el Excel
    # Solo con "interesado" - NO tiene conPack=true
    data = {
        "telefono": "689541566",
        "firstName": "MIGUEL ARTURO",
        "lastName": "HINOJOSA HICIANO", 
        "interesado": "interesado",
        "phoneNumber": "+34689541566",
        "codigoPostal": "28803",
        "delegacion": "281",
        "fechaNacimiento": "19920129",
        "sexo": "VARÓN",
        "agentName": "Ana Martín",
        "sr_sra": "señor"
        # NOTA: NO incluye conPack=true, por lo que debe ser "Sin Pack"
    }
    
    print("PROBANDO CON LEAD REAL - SIN CONPACK")
    print("="*50)
    print("Lead: MIGUEL ARTURO HINOJOSA HICIANO")
    print("Telefono: 689541566")
    print("Datos enviados (SIN conPack=true):")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\nAPI exitosa - Debería marcar como 'Cita Agendada' + 'Sin Pack'")
        else:
            print(f"Error API: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_lead_real()
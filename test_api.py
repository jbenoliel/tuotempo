import requests
import json
import re

def crear_usuario(fname, lname, phone, birthday="01/01/1980", privacy="1", onetime_user="1"):
    """Crea un usuario en TuoTempo y devuelve el ID del miembro creado"""
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/users"
    
    payload = {
        "fname": fname,
        "lname": lname,
        "privacy": privacy,
        "birthday": birthday,
        "phone": phone,
        "Onetime_user": onetime_user
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Cookie': 'lang=es'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Código de estado: {response.status_code}")
        
        # Extraer el memberid usando expresiones regulares
        # Esto es más robusto que intentar parsear un JSON malformado
        member_id_match = re.search(r'"memberid":\s*"([^"]+)"', response.text)
        result_match = re.search(r'"result":\s*"([^"]+)"', response.text)
        
        result = result_match.group(1) if result_match else "UNKNOWN"
        member_id = member_id_match.group(1) if member_id_match else None
        
        print(f"Resultado: {result}")
        print(f"ID de miembro: {member_id}")
        
        return {
            "success": result == "OK",
            "member_id": member_id,
            "raw_response": response.text
        }
        
    except Exception as e:
        print(f"Error al realizar la solicitud: {e}")
        return {"success": False, "error": str(e)}

# Ejemplo de uso
if __name__ == "__main__":
    resultado = crear_usuario(
        fname="RAUL", 
        lname="PRUEBA", 
        phone="670252676", 
        birthday="02/07/1973"
    )
    
    if resultado["success"]:
        print(f"\n¡Usuario creado exitosamente con ID: {resultado['member_id']}!")
    else:
        print("\nError al crear el usuario.")


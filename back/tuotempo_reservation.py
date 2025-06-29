import requests
import json
import re
from datetime import datetime

def crear_reserva(userid, resourceid, activityid, start_date, start_time, end_time, 
                provider_session_id, searchid, portal_activityid=None, 
                areaid=None, phone=None, email=None, tags=None, is_remote=False):
    """
    Crea una reserva en TuoTempo según la documentación oficial
    
    Parámetros obligatorios:
    - userid: ID del usuario/cliente (memberid)
    - resourceid: ID del recurso (médico)
    - activityid: ID de la actividad
    - start_date: Fecha de inicio (formato: "DD/MM/YYYY")
    - start_time: Hora de inicio (formato: "HH:MM")
    - end_time: Hora de fin (formato: "HH:MM")
    - provider_session_id: ID de sesión del proveedor (de Availabilities:Search)
    - searchid: ID de búsqueda (de Availabilities:Search)
    
    Parámetros opcionales:
    - portal_activityid: ID de actividad del portal (obligatorio para instancias PORTAL)
    - areaid: ID del área
    - phone: Teléfono para notificaciones (communication_phone)
    - email: Email para notificaciones (communication_email)
    - tags: Etiquetas de la reserva
    - is_remote: Si la reserva es remota (1) o presencial (0)
    
    Retorna:
    - Diccionario con el resultado de la operación
    """
    url = "https://app.tuotempo.com/api/v3/tt_portal_adeslas/reservations"
    
    # Payload con campos obligatorios según documentación
    payload = {
        "userid": userid,
        "resourceid": resourceid,
        "start_date": start_date,  # DD/MM/YYYY
        "startTime": start_time,   # HH:MM
        "endTime": end_time,       # HH:MM
        "activityid": activityid,
        "provider_session_id": provider_session_id,
        "searchid": searchid
    }
    
    # Añadir campos obligatorios para instancias PORTAL
    if portal_activityid:
        payload["portal_activityid"] = portal_activityid
    
    # Añadir campos opcionales si se proporcionan
    if areaid:
        payload["areaid"] = areaid
        
    if is_remote:
        payload["remote"] = 1
    
    if phone:
        payload["communication_phone"] = phone
        
    if email:
        payload["communication_email"] = email
        
    if tags:
        payload["tags"] = tags
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 24b98d8d41b970d38362b52bd3505c04',
        'Cookie': 'lang=es'
    }
    
    print(f"\nCreando reserva para usuario {userid}")
    print(f"JSON enviado:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\nCódigo de estado: {response.status_code}")
        
        # Extraer información relevante usando regex (para manejar JSON malformado)
        result_match = re.search(r'"result":\s*"([^"]+)"', response.text)
        msg_match = re.search(r'"msg":\s*"([^"]+)"', response.text)
        
        result = result_match.group(1) if result_match else "UNKNOWN"
        msg = msg_match.group(1) if msg_match else "Sin mensaje"
        
        print(f"Resultado: {result}")
        print(f"Mensaje: {msg}")
        
        return {
            "success": result == "OK",
            "result": result,
            "message": msg,
            "raw_response": response.text
        }
        
    except Exception as e:
        print(f"\nError al realizar la solicitud: {e}")
        return {"success": False, "error": str(e)}

# Función auxiliar para convertir formato de fecha
def convertir_formato_fecha(fecha_iso):
    """Convierte fecha de formato ISO (YYYY-MM-DD) a formato TuoTempo (DD/MM/YYYY)"""
    try:
        fecha_dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
        return fecha_dt.strftime("%d/%m/%Y")
    except ValueError:
        # Si ya está en formato DD/MM/YYYY, devolverlo tal cual
        return fecha_iso

# Ejemplo de uso
if __name__ == "__main__":
    # Datos de ejemplo (reemplazar con valores reales)
    resultado = crear_reserva(
        userid="sc16859596caff25",
        resourceid="sc12345678",  # Reemplazar con ID válido
        activityid="sc159232371eb9c1",
        start_date="01/07/2025",  # Formato DD/MM/YYYY
        start_time="10:00",       # Formato HH:MM
        end_time="10:30",         # Formato HH:MM
        provider_session_id="session123",  # De Availabilities:Search
        searchid="search456",             # De Availabilities:Search
        portal_activityid="portal789",    # Para instancias PORTAL
        phone="670252676",
        tags="WEB_NO_ASEGURADO"
    )
    
    if resultado["success"]:
        print("\n✅ Reserva creada exitosamente")
    else:
        print(f"\n❌ Error al crear la reserva: {resultado.get('message', '')}")

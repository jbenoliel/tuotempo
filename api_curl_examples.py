import json
import urllib.parse
from tuotempo_api import TuoTempoAPI

def generate_curl_command(method, url, headers, params=None, data=None):
    """
    Genera un comando curl equivalente a una llamada HTTP
    """
    # Iniciar el comando curl
    curl_command = f'curl -X {method} '
    
    # Agregar headers
    for key, value in headers.items():
        curl_command += f'-H "{key}: {value}" '
    
    # Agregar parámetros de consulta a la URL
    if params:
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        url = f"{url}?{query_string}"
    
    # Agregar datos del body para POST/PUT
    if data:
        if isinstance(data, dict):
            data_str = json.dumps(data)
            curl_command += f'-d \'{data_str}\' '
        else:
            curl_command += f'-d \'{data}\' '
    
    # Agregar la URL
    curl_command += f'"{url}"'
    
    return curl_command

def main():
    # Inicializar el cliente de API
    api = TuoTempoAPI(
        lang="es",
        environment="PRE"  # Usar entorno PRE
    )
    
    # Obtener la base URL y el ID de instancia
    base_url = api.base_url
    instance_id = api.instance_id
    
    print("=== EJEMPLOS DE COMANDOS CURL PARA LA API DE TUOTEMPO ===\n")
    
    # 1. Ejemplo para obtener centros
    centers_url = f"{base_url}/{instance_id}/areas"
    centers_params = {"lang": api.lang}
    centers_curl = generate_curl_command("GET", centers_url, api.headers, centers_params)
    
    print("1. OBTENER LISTA DE CENTROS")
    print(centers_curl)
    print("\n")
    
    # 2. Ejemplo para obtener slots disponibles
    area_id = "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44gowswy_sejh"  # Adeslas Dental Badalona
    activity_id = "sc159232371eb9c1"  # Primera Visita (mayores De 16 Años)
    start_date = "23/06/2025"  # Formato DD/MM/YYYY
    
    slots_url = f"{base_url}/{instance_id}/availabilities"
    slots_params = {
        "lang": api.lang,
        "activityid": activity_id,
        "areaId": area_id,
        "start_date": start_date,
        "bypass_availabilities_fallback": "true"
    }
    slots_curl = generate_curl_command("GET", slots_url, api.headers, slots_params)
    
    print("2. OBTENER SLOTS DISPONIBLES")
    print(slots_curl)
    print("\n")
    
    # 3. Ejemplo para confirmar una cita (requiere token Bearer)
    confirm_url = f"{base_url}/{instance_id}/reservations"
    
    # Para confirmar cita se necesita el token Bearer
    auth_headers = api.headers.copy()
    auth_headers["Authorization"] = f"Bearer {api.api_key}"
    
    # Datos de ejemplo para confirmar cita
    confirm_data = {
        "lang": api.lang,
        "provider_session_id": "ResourceLid::EC6XPD4F-EF3EWL7A-II4Z3VTE-44GOWSWY-SHJH@AreaLid::ECEXPD4F-EF3EWL7A-EI4Z3VEE-44GOWSWY-SEJH@Availability_lid::EC6XPD4F-EF3EWL7A-II4Z3VTE-44GOWSWY-SHJH_4034_202507011330:20@ActivityPrice::0",
        "client": {
            "name": "Nombre",
            "surname": "Apellido",
            "email": "ejemplo@correo.com",
            "mobile": "600000000",
            "idnumber": "12345678Z"
        }
    }
    
    confirm_curl = generate_curl_command("POST", confirm_url, auth_headers, data=confirm_data)
    
    print("3. CONFIRMAR UNA CITA (con token Bearer)")
    print(confirm_curl)
    print("\n")
    
    # 4. Información sobre los headers y autenticación
    print("=== INFORMACIÓN SOBRE HEADERS Y AUTENTICACIÓN ===")
    print("- Headers básicos para todas las llamadas:")
    print(f'  "content-type": "application/json; charset=UTF-8"')
    print("\n- Para llamadas que requieren autenticación, añadir:")
    print(f'  "Authorization": "Bearer TU_API_KEY"')
    print("\n- Llamadas que NO requieren token Bearer:")
    print("  - GET /areas (obtener centros)")
    print("  - GET /availabilities (obtener slots disponibles)")
    print("\n- Llamadas que SÍ requieren token Bearer:")
    print("  - POST /reservations (confirmar cita)")
    print("  - POST /clients (registrar usuario)")
    
    # 5. Estructura de la respuesta JSON
    print("\n=== ESTRUCTURA DE LA RESPUESTA JSON ===")
    print("La respuesta de la API tiene la siguiente estructura general:")
    print("""
{
  "result": "OK",  // "OK" si la llamada fue exitosa, "KO" si hubo un error
  "return": {
    "results": {
      "availabilities": [  // Lista de slots disponibles
        {
          "start_date": "01/07/2025",  // Fecha de la cita (DD/MM/YYYY)
          "startTime": "13:30",        // Hora de inicio
          "endTime": "13:50",          // Hora de fin
          "resourceName": "Gral Dra.Felisoni",  // Nombre del profesional
          "areaTitle": "Adeslas Dental Badalona",  // Nombre del centro
          "activityTitle": "Primera Visita",  // Nombre de la actividad
          "provider_session_id": "ResourceLid::EC6XPD4F-EF3EWL7A-II4Z3VTE-44GOWSWY-SHJH@AreaLid::ECEXPD4F-EF3EWL7A-EI4Z3VEE-44GOWSWY-SEJH@Availability_lid::EC6XPD4F-EF3EWL7A-II4Z3VTE-44GOWSWY-SHJH_4034_202507011330:20@ActivityPrice::0"
          // ... otros campos
        },
        // ... más slots disponibles
      ]
    }
  }
}
    """)

if __name__ == "__main__":
    main()

import requests
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TuoTempoAPI:
    """
    Client for TuoTempo API integration.
    
    This class handles all API calls to TuoTempo services following the specified flow:
    1. Obtener centros (Get centers)
    2. Obtener huecos (Get available slots)
    3. Registrar no asegurado (Register non-insured user)
    4. Confirmar cita (Confirm appointment)
    """
    
    def __init__(self, instance_id=None, lang="es", api_key=None, environment="PRE"):
        """
        Initialize the TuoTempo API client.
        
        Args:
            instance_id (str): The instance ID for TuoTempo API. Default is None, which will use the environment variable.
            lang (str): Language code for responses. Options: "es" (Spanish), "en" (English), "ca" (Catalan).
            api_key (str): API key for authentication. Default is None, which will use the environment variable.
            environment (str): Environment to use ("PRE" or "PRO"). Default is "PRE".
        """
        self.base_url = "https://app.tuotempo.com/api/v3"
        self.instance_id = instance_id or os.getenv("TUOTEMPO_INSTANCE_ID", "tt_portal_adeslas")
        self.lang = lang
        self.environment = environment
        self.headers = {
            "content-type": "application/json; charset=UTF-8"
        }
        self.session_id = None
        self.member_id = None
        
        # Set API key based on environment
        if api_key:
            self.api_key = api_key
        else:
            # Default API keys for VOICEBOT2
            pre_key = "3a5835be0f540c7591c754a2bf0758bb"  # PRE environment
            pro_key = "24b98d8d41b970d38362b52bd3505c04"  # PRO environment
            self.api_key = pre_key if environment == "PRE" else pro_key

    def get_centers(self, province=None):
        """
        Get the list of all centers (clinics).
        
        Endpoint: GET /areas
        
        Args:
            province (str, optional): Province filter to limit centers to a specific province
        
        Returns:
            dict: JSON response with centers information
        """
        url = f"{self.base_url}/{self.instance_id}/areas"
        params = {"lang": self.lang}
        
        # Add province filter if provided
        if province:
            params["province"] = province

        logging.info(f"[TuoTempoAPI] GET Centers - URL: {url}, Params: {params}")
        response = requests.get(url, headers=self.headers, params=params)
        logging.info(f"[TuoTempoAPI] GET Centers - Response: {response.status_code}")
        return response.json()
    
    def get_available_slots(self, activity_id, area_id, start_date, resource_id=None, time_preference=None, min_time=None, max_time=None):
        """
        Get available slots for a specific service, center, and date.
        
        Endpoint: GET /availabilities
        
        Args:
            activity_id (str): Service ID to search for
            area_id (str): Center ID where the service is provided
            start_date (str): Start date in DD/MM/YYYY format
            resource_id (str, optional): Specialist ID.
        
        Returns:
            dict: JSON response with available slots
        """
        from datetime import datetime
        
        # Ensure start_date is today or later
        try:
            provided_date = datetime.strptime(start_date, "%d/%m/%Y")
            if provided_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                start_date = datetime.now().strftime("%d/%m/%Y")
        except (ValueError, IndexError):
            pass

        url = f"{self.base_url}/{self.instance_id}/availabilities"
        params = {
            "lang": self.lang,
            "activityid": activity_id,
            "areaId": area_id,
            "start_date": start_date,
            "bypass_availabilities_fallback": "true"
        }
        # Añadir filtros de franja horaria si se solicitan
        if time_preference:
            pref = time_preference.upper()
            if pref == 'MORNING':
                params['minTime'] = '360'  # 06:00
                params['maxTime'] = '900'  # 15:00
            elif pref == 'AFTERNOON':
                params['minTime'] = '900'  # 15:00
                params['maxTime'] = '1260' # 21:00
        # Sobrescribir si se pasan min_time/max_time explícitos
        if min_time:
            params['minTime'] = str(min_time)
        if max_time:
            params['maxTime'] = str(max_time)
        
        if resource_id:
            params["resourceId"] = resource_id

        logging.info(f"[TuoTempoAPI] GET Availabilities - URL: {url}, Params: {params}")
        response = requests.get(url, headers=self.headers, params=params)
        logging.info(
            f"[TuoTempoAPI] GET Availabilities - Response: {response.status_code}, Body: {response.text[:500]}"
        )
        # Devolver el JSON si es posible; si falla, devolver texto crudo para depuración
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text, "status_code": response.status_code}
    
    def register_non_insured_user(self, fname, lname, birthday, phone):
        """
        Register a non-insured user in TuoTempo.
        
        Endpoint: POST /users
        
        Args:
            fname (str): First name of the appointment recipient
            lname (str): Last name of the appointment recipient
            birthday (str): Birth date of the appointment recipient
            phone (str): Phone number associated with the appointment
        
        Returns:
            dict: JSON response with user registration information
            
        Note:
            This method sets the session_id attribute which is required for confirming appointments.
        """
        url = f"{self.base_url}/{self.instance_id}/users"
        params = {"lang": self.lang}
        
        # Sanitize input to prevent issues with spaces or invisible characters
        payload = {
            "fname": fname.strip() if fname else "",
            "lname": lname.strip() if lname else "",
            "privacy": "1",  # Indicates that privacy policy has been accepted
            "birthday": birthday.strip() if birthday else "",
            "phone": phone.strip() if phone else "",
            "onetime_user": "1"  # Indicates that this is a temporary user linked to a single appointment
        }
        
        logging.info(f"[TuoTempoAPI] POST Register User - URL: {url}, Payload: {json.dumps(payload)}")
        response = requests.post(url, headers=self.headers, params=params, json=payload)
        response_data = response.json()
        logging.info(f"[TuoTempoAPI] POST Register User - Response: {response.status_code}, Body: {response.text[:200]}")
        
        # Store session ID for later use in confirming appointments.
        # The sessionid can be at the root or nested inside user_info.
        user_info = response_data.get("user_info", {})
        session_id = response_data.get("sessionid") or user_info.get("sessionid")
        
        if session_id:
            self.session_id = session_id
            logging.info(f"[TuoTempoAPI] SessionID extraído y guardado: {self.session_id}")
        else:
            logging.warning("[TuoTempoAPI] No se encontró 'sessionid' en la respuesta de registro de usuario.")

        member_id = user_info.get("memberid")
        if member_id:
            self.member_id = member_id
            logging.info(f"[TuoTempoAPI] MemberID extraído y guardado: {self.member_id}")
        else:
            logging.warning("[TuoTempoAPI] No se encontró 'memberid' en la respuesta de registro de usuario.")
        
        return response_data
    
    def confirm_appointment(self, availability, communication_phone):
        """
        Confirma una cita en Tuotempo con los datos de disponibilidad y el usuario registrado
        
        Args:
            availability (dict): Información de disponibilidad de la cita
            communication_phone (str): Teléfono de contacto
            
        Returns:
            dict: Respuesta de la API
        """
        if not self.member_id:
            raise ValueError("No member ID available. Please register a user first.")
            
        # Crear la URL para la confirmación de cita
        endpoint = "/reservations"
        url = f"{self.base_url}/{self.instance_id}{endpoint}"
        
        # Preparar payload con datos de la cita
        payload = {}
        
        # Copiar datos de availability a payload
        for key in ["activityid", "resourceid", "startTime", "start_date", "endTime"]:
            if key in availability:
                payload[key] = availability[key]
        
        # Añadir datos adicionales usando los nombres de campo correctos (con mayúscula inicial)
        payload.update({
            "userid": self.member_id.strip() if self.member_id else "",
            "Communication_phone": communication_phone.strip(),  # C mayúscula
            "Tags": "WEB_NO_ASEGURADO",  # T mayúscula
            "isExternalPayment": "false"
        })
        
        # Usar el API_KEY como Bearer token, no el session_id
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        logging.info(f"[TuoTempoAPI] POST Confirm Appointment - URL: {url}")
        logging.info(f"[TuoTempoAPI] Headers: {headers}")
        logging.info(f"[TuoTempoAPI] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        response = requests.post(url, headers=headers, json=payload)
        
        logging.info(f"[TuoTempoAPI] POST Confirm Appointment - Response: {response.status_code}")
        logging.info(f"[TuoTempoAPI] Body: {response.text[:500] + '...' if len(response.text) > 500 else response.text}")

        try:
            return response.json()
        except json.JSONDecodeError as e:
            logging.error(f"[TuoTempoAPI] Error al decodificar JSON de respuesta: {e}")
            return {"result": "ERROR", "msg": "Respuesta inválida de la API", "details": response.text}
    
    def cancel_appointment(self, resid, reason=""):
        """
        Cancela una cita existente.

        Endpoint: DELETE /reservations/{resid}

        Args:
            resid (str): ID de la reserva devuelto al crear la cita
            reason (str, optional): Motivo de la cancelación (si el API lo requiere)

        Returns:
            dict: Respuesta de la API
        """
        if not resid:
            raise ValueError("'resid' es obligatorio para cancelar la cita")

        endpoint = f"/reservations/{resid}"
        url = f"{self.base_url}/{self.instance_id}{endpoint}"

        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"

        params = {"lang": self.lang}
        payload = {"reason": reason} if reason else None

        logging.info(f"[TuoTempoAPI] DELETE Cancel Appointment - URL: {url}")
        response = requests.delete(url, headers=headers, params=params, json=payload)
        logging.info(f"[TuoTempoAPI] DELETE Cancel Appointment - Response: {response.status_code}")
        logging.info(f"[TuoTempoAPI] Body: {response.text[:500] + '...' if len(response.text) > 500 else response.text}")

        try:
            return response.json()
        except json.JSONDecodeError as e:
            logging.error(f"[TuoTempoAPI] Error al decodificar JSON de respuesta: {e}")
            return {"result": "ERROR", "msg": "Respuesta inválida de la API", "details": response.text}

    def handle_error(self, response):
        """
        Handle API error responses based on the exception type.
        
        Args:
            response (dict): API response containing error information
        
        Returns:
            dict: Error information with message and recommended action
        """
        exception = response.get("exception")
        msg = response.get("msg", "Unknown error")
        
        if exception == "TUOTEMPO_RESOURCE_NOT_ALLOWED":
            action = "No slots found for the specified criteria. Try again with different filters or contact an agent."
        elif exception == "TUOTEMPO_MAX_RES_BOOKED_ONLINE":
            action = msg  # Show the message from the API
        elif exception in ["PROVIDER_RESERVATION_CONFLICT_ERROR", "MEMBER_RESERVATION_CONFLICT_ERROR"]:
            action = "The slot is no longer available. Please try selecting another available slot."
        else:
            action = f"An error occurred: {msg}"
        
        return {
            "error": exception,
            "message": msg,
            "recommended_action": action
        }

import requests
import json
import os
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
        
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def get_available_slots(self, activity_id, area_id, start_date, resource_id=None, min_time=None, max_time=None):
        """
        Get available slots for a specific service, center, and date.
        
        Endpoint: GET /availabilities
        
        Args:
            activity_id (str): Service ID to search for (e.g., "sc159232371eb9c1" for first visit to general dentistry)
            area_id (str): Center ID obtained from get_centers()
            start_date (str): Start date in DD/MM/YYYY format (must be today or later)
            resource_id (str, optional): Specialist ID. If not provided, slots for all specialists will be returned.
            min_time (str, optional): Minimum time frame to consider:
                - None: any time frame
                - "360": morning only
                - "900": afternoon only
            max_time (str, optional): Maximum time frame to consider:
                - None: any time frame
                - "900": morning only
                - "1260": afternoon only
        
        Returns:
            dict: JSON response with available slots
        """
        # Validate that start_date is today or later
        from datetime import datetime
        
        # Ensure start_date is in the correct format
        if start_date:
            try:
                # Parse the provided date (DD/MM/YYYY)
                date_parts = start_date.split('/')
                if len(date_parts) == 3:
                    day, month, year = map(int, date_parts)
                    provided_date = datetime(year, month, day)
                    
                    # Get today's date
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # Ensure the date is today or later
                    if provided_date < today:
                        # If date is in the past, use today's date
                        today_str = datetime.now().strftime("%d/%m/%Y")
                        start_date = today_str
            except (ValueError, IndexError):
                # If there's any error parsing the date, keep the original value
                pass
        
        url = f"{self.base_url}/{self.instance_id}/availabilities"
        params = {
            "lang": self.lang,
            "activityid": activity_id,
            "areaId": area_id,
            "start_date": start_date,
            "bypass_availabilities_fallback": "true"  # Avoid searching in other locations if no slots are found
        }
        
        # Add optional parameters if provided
        if resource_id:
            params["resourceId"] = resource_id
        if min_time:
            params["minTime"] = min_time
        if max_time:
            params["maxTime"] = max_time
        
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
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
        
        response = requests.post(url, headers=self.headers, params=params, json=payload)
        response_data = response.json()
        
        # Store session ID for later use in confirming appointments
        if response_data.get("result") == "OK" and "sessionid" in response_data:
            self.session_id = response_data["sessionid"]
        
        return response_data
    
    def confirm_appointment(self, availability, communication_phone):
        """
        Reserve an appointment associated with a specific user.
        
        Endpoint: POST /reservations
        
        Args:
            availability (dict): Selected availability from get_available_slots() response
            communication_phone (str): Contact phone number provided during user registration
        
        Returns:
            dict: JSON response with appointment confirmation information
        
        Raises:
            ValueError: If no session_id is available (user not registered)
        """
        if not self.session_id:
            raise ValueError("No session ID available. Please register a user first.")
        
        url = f"{self.base_url}/{self.instance_id}/reservations"
        params = {"lang": self.lang}
        
        # Create a copy of the availability and add required fields
        # Make sure to create a new dict to avoid modifying the original
        payload = {}
        if isinstance(availability, dict):
            payload = {k: v for k, v in availability.items()}
        
        # Add required fields, ensuring all values are properly sanitized
        payload.update({
            "userid": self.session_id.strip() if self.session_id else "",
            "communication_phone": communication_phone.strip(),
            "tags": "WEB_NO_ASEGURADO",
            "isExternalPayment": "false"
        })
        
        # Add authorization header with Bearer token
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Debug: mostrar llamada completa
        print("\n=== DEBUG /reservations ===")
        print("URL:", url)
        print("Params:", params)
        print("Headers:", headers)
        print("Payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("===========================\n")
        response = requests.post(url, headers=headers, params=params, json=payload)
        
        # Debug: mostrar respuesta completa
        print("\n=== DEBUG RESPUESTA /reservations ===")
        print("Status code:", response.status_code)
        print("Headers:", dict(response.headers))
        print("Contenido:", response.text[:500] + "..." if len(response.text) > 500 else response.text)
        print("===========================\n")
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            return response.text
    
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

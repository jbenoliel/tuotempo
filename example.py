import json
import requests
from tuotempo_api import TuoTempoAPI
from datetime import datetime

def print_json(data):
    """Print JSON data in a readable format"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def debug_request(url, method, headers, params=None, data=None):
    """Print request details for debugging"""
    print(f"\n--- DEBUG: {method} {url} ---")
    print(f"Headers: {headers}")
    if params:
        print(f"Params: {params}")
    if data:
        print(f"Data: {data}")
    print("---")

def main():
    # Initialize the TuoTempo API client with API key for PRE environment
    api = TuoTempoAPI(
        lang="es",  # Use Spanish language
        api_key="3a5835be0f540c7591c754a2bf0758bb",  # PRE environment API key for VOICEBOT2
        environment="PRE"  # Use PRE environment
    )
    
    # Step 1: Get centers (Obtener centros)
    print("Getting centers...")
    # Especificar una provincia para filtrar los centros por nombre
    province = "Madrid"
    print(f"Searching centers in province: {province}")
    
    # Patch the requests methods to print debug info
    original_get = requests.get
    original_post = requests.post
    
    def debug_get(*args, **kwargs):
        debug_request(args[0], "GET", kwargs.get('headers', {}), kwargs.get('params', {}))
        return original_get(*args, **kwargs)
        
    def debug_post(*args, **kwargs):
        debug_request(args[0], "POST", kwargs.get('headers', {}), kwargs.get('params', {}), kwargs.get('json', {}))
        response = original_post(*args, **kwargs)
        print(f"Response status code: {response.status_code}")
        return response
        
    requests.get = debug_get
    requests.post = debug_post
    
    centers_response = api.get_centers(province=province)
    
    # Restore original methods
    requests.get = original_get
    requests.post = original_post
    
    # Print the full response
    print("\nFull response:")
    print_json(centers_response)
    
    if centers_response.get("result") != "OK":
        print("Error getting centers:")
        print_json(api.handle_error(centers_response))
        return
    
    # Print centers information
    centers = centers_response.get('return', {}).get('results', [])
    print(f"Found {len(centers)} centers")
    
    # For demonstration, select the first center
    if centers:
        first_center = centers[0]
        print(f"Selected center: {first_center.get('areaTitle')}")
        area_id = first_center.get("areaid")
        
        # Step 2: Get available slots (Obtener huecos)
        print("\nGetting available slots...")
        # Use fixed activity ID for first visit to general dentistry
        activity_id = "sc159232371eb9c1"
        # Use current date in DD/MM/YYYY format
        today = datetime.now()
        start_date = today.strftime("%d/%m/%Y")  # Use today's date
        
        slots_response = api.get_available_slots(
            activity_id=activity_id,
            area_id=area_id,
            start_date=start_date
        )
        
        if slots_response.get("result") != "OK":
            print("Error getting available slots:")
            print_json(api.handle_error(slots_response))
            return
        
        availabilities = slots_response.get("return", {}).get("results", {}).get("availabilities", [])
        print(f"Found {len(availabilities)} available slots")
        
        # For demonstration, select the first available slot
        if availabilities:
            selected_slot = availabilities[0]
            print(f"Selected slot: {selected_slot.get('start_date')} at {selected_slot.get('startTime')}")
            
            # Step 3: Register non-insured user (Registrar no asegurado)
            print("\nRegistering user...")
            user_response = api.register_non_insured_user(
                fname="Juan",
                lname="Pérez",
                birthday="01/01/1980",
                phone="600123456"
            )
            
            if user_response.get("result") != "OK":
                print("Error registering user:")
                print_json(user_response)
                # Si hay una excepción específica, usar handle_error
                if "exception" in user_response:
                    print("Error details:")
                    print_json(api.handle_error(user_response))
                return
            
            print(f"User registered successfully with session ID: {api.session_id}")
            
            # Step 4: Confirm appointment (Confirmar cita)
            print("\nConfirming appointment...")
            appointment_response = api.confirm_appointment(
                availability=selected_slot,
                communication_phone="600123456"
            )
            
            if appointment_response.get("result") != "OK":
                print("Error confirming appointment:")
                print_json(api.handle_error(appointment_response))
                return
            
            print("Appointment confirmed successfully!")
            print(f"Appointment ID: {appointment_response.get('return')}")
            
            # Print appointment details
            if "additional_return" in appointment_response:
                details = appointment_response["additional_return"]
                print(f"Date: {details.get('start_date')} at {details.get('startTime')}")
                print(f"Center: {details.get('areaTitle')}")
                print(f"Address: {details.get('address')}, {details.get('cp')}, {details.get('province')}")
                print(f"Service: {details.get('activityTitle')}")
                print(f"Specialist: {details.get('resourceName')}")
        else:
            print("No available slots found for the selected criteria.")
    else:
        print("No centers found.")

if __name__ == "__main__":
    main()

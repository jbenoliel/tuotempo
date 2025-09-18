import requests
import json

# URL of the local API endpoint that calls the Tuotempo API
# This endpoint is defined in api_tuotempo.py and uses the Tuotempo class
url = "https://web-production-b743.up.railway.app/api/obtener_slots"

# Parameters needed for the endpoint
# Using a valid areaId found in other test scripts
params = {
    'areaId': 'default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44kowswy_sejh',
    'activityId': 'sc159232371eb9c1',
    'startDate': '10-07-2025' # A future date
}

print(">>> Triggering a call to the local Tuotempo API wrapper...")
print(f">>> Endpoint: {url}")
print(f">>> Params: {json.dumps(params)}")

try:
    # Make the request to the local Flask application
    response = requests.get(url, params=params)
    
    print(f"\n<<< Local API Response Status: {response.status_code}")
    
    # Try to print JSON response, or text if it fails
    try:
        print("<<< Local API Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print("<<< Local API Response Text:")
        print(response.text)

    print("\n>>> This action should have created or updated the 'logs/tuotempo_api.log' file.")

except requests.exceptions.ConnectionError as e:
    print(f"\nXXX ERROR: Could not connect to the local Flask application.")
    print("XXX Please make sure the application is running on http://localhost:5000.")
    print(f"XXX Details: {e}")
except Exception as e:
    print(f"\nXXX An unexpected error occurred: {e}")

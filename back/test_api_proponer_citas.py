import requests

url = "http://127.0.0.1:5001/api/proponer_citas"

payload = {
    "fecha1": "2025-07-01",
    "hora1": "10:00",
    "fecha2": "2025-07-01",
    "hora2": "12:30",
    "fecha3": "2025-07-02",
    "hora3": "16:00"
}

response = requests.post(url, json=payload)

if response.ok:
    print("Respuesta de la API:")
    print(response.json()["respuesta"])
else:
    print("Error:", response.status_code, response.text)

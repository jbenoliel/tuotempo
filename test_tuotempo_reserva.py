#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para probar la secuencia completa de reserva de citas en TuoTempo:
1. GET /availabilities - Obtener disponibilidad
2. POST /users - Registrar usuario no asegurado
3. POST /reservations - Confirmar reserva de cita
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Configuración de la API
BASE_URL = "https://app.tuotempo.com/api/v3"
INSTANCE_ID = "tt_portal_adeslas"
API_KEY = "24b98d8d41b970d38362b52bd3505c04"  # API key para entorno PRO

# Datos para la prueba
ACTIVITY_ID = "sc159232371eb9c1"  # ID de actividad para primera visita a odontología general

# Lista de clínicas para probar
CLINICS = [
    "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44kowswy_sejh",  # Adeslas Dental Badalona
    "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44kowswy_sejh",  # Clínica 2
    "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44kowswy_sejh"   # Clínica 3
]

START_DATE = "10-07-2025"  # Formato DD-MM-YYYY (10 de julio)
PHONE = "+34629203315"
FNAME = "Jacques"
LNAME = "Benoliel"
BIRTHDAY = "17/10/1961"  # Formato DD/MM/YYYY

def print_separator():
    """Imprime una línea separadora para mejorar la legibilidad"""
    print("\n" + "="*80 + "\n")

def get_availabilities(start_date=None, area_id=None):
    """
    Paso 1: Obtener disponibilidades
    GET /availabilities
    
    Args:
        start_date (str, optional): Fecha de inicio en formato DD-MM-YYYY. Si es None, usa START_DATE global.
        area_id (str, optional): ID de la clínica. Si es None, usa la primera clínica de CLINICS.
    """
    search_date = start_date or START_DATE
    clinic_id = area_id or CLINICS[0]
    
    print(f"PASO 1: OBTENIENDO DISPONIBILIDADES PARA FECHA {search_date} EN CLÍNICA {clinic_id}")
    
    # Construir la URL correctamente
    url = f"{BASE_URL}/{INSTANCE_ID}/availabilities"
    
    # Parámetros de la solicitud
    params = {
        "lang": "es",
        "activityid": ACTIVITY_ID,
        "areaId": clinic_id,
        "start_date": search_date,
        "bypass_availabilities_fallback": "true",
        "maxResults": "10"
    }
    
    # Encabezados
    headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    print(f"URL: {url}")
    print(f"Parámetros: {json.dumps(params, indent=2)}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        
        data = response.json()
        print(f"\nCódigo de respuesta: {response.status_code}")
        print(f"Resultado: {data.get('result', 'N/A')}")
        
        # Guardar la respuesta completa en un archivo para análisis
        with open("availabilities_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Respuesta completa guardada en 'availabilities_response.json'")
        
        # Extraer y mostrar algunas disponibilidades
        if data.get("result") == "OK":
            availabilities = data.get("return", {}).get("results", {}).get("availabilities", [])
            print(f"\nSe encontraron {len(availabilities)} disponibilidades")
            
            if availabilities:
                # Mostrar las primeras 3 disponibilidades
                print("\nPrimeras disponibilidades encontradas:")
                for i, slot in enumerate(availabilities[:3]):
                    print(f"{i+1}. Fecha: {slot.get('start_date')} - Hora: {slot.get('startTime')} a {slot.get('endTime')}")
                
                # Seleccionar la primera disponibilidad para la siguiente prueba
                selected_slot = availabilities[0]
                print(f"\nSeleccionando para reserva: {selected_slot.get('start_date')} a las {selected_slot.get('startTime')}")
                return selected_slot
            else:
                print("\nNo se encontraron disponibilidades para los criterios especificados.")
                print(f"Mensaje del servidor: {data.get('msg', 'No hay mensaje adicional')}")
                print("\nSugerencias:")
                print("1. Intente con una fecha posterior")
                print("2. Verifique que el ID de actividad y área sean correctos")
                print("3. Pruebe con otro centro dental")
                return None
        else:
            print(f"Error en la respuesta: {data.get('error', 'Error desconocido')}")
            return None
            
    except Exception as e:
        print(f"Error al obtener disponibilidades: {str(e)}")
        return None

def register_user():
    """
    Paso 2: Registrar usuario no asegurado
    POST /users
    """
    print_separator()
    print("PASO 2: REGISTRANDO USUARIO NO ASEGURADO")
    
    url = f"{BASE_URL}/{INSTANCE_ID}/users"
    
    # Datos del usuario
    payload = {
        "fname": FNAME,
        "lname": LNAME,
        "privacy": "1",
        "phone": PHONE,
        "Onetime_user": "1",
        "birthday": BIRTHDAY
    }
    
    # Encabezados
    headers = {
        "Cookie": "lang=es",
        "Content-Type": "application/json"
    }
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        print(f"\nCódigo de respuesta: {response.status_code}")
        print(f"Resultado: {data.get('result', 'N/A')}")
        
        # Guardar la respuesta completa en un archivo para análisis
        with open("user_registration_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Respuesta completa guardada en 'user_registration_response.json'")
        
        if data.get("result") == "OK":
            user_id = data.get("return", {}).get("memberid")
            print(f"\nUsuario registrado con éxito. ID: {user_id}")
            return user_id
        else:
            print(f"Error al registrar usuario: {data.get('error', 'Error desconocido')}")
            return None
            
    except Exception as e:
        print(f"Error al registrar usuario: {str(e)}")
        return None

def make_reservation(user_id, slot):
    """
    Paso 3: Confirmar reserva de cita
    POST /reservations
    
    Args:
        user_id (str): ID del usuario registrado (memberid)
        slot (dict): Información del slot seleccionado
    """
    print_separator()
    print("PASO 3: CONFIRMANDO RESERVA DE CITA")
    
    if not user_id or not slot:
        print("No se puede realizar la reserva sin un ID de usuario y un slot seleccionado.")
        print(f"ID de usuario recibido: {user_id}")
        print(f"Slot recibido: {slot}")
        return None
    
    url = f"{BASE_URL}/{INSTANCE_ID}/reservations"
    
    # Preparar datos para la reserva
    start_date = slot.get("start_date", "")  # Ya viene en formato DD/MM/YYYY
    
    payload = {
        "userid": user_id,
        "Communication_phone": PHONE,
        "Tags": "WEB_NO_ASEGURADO",
        "activityid": ACTIVITY_ID,
        "isExternalPayment": "false",
        "startTime": slot.get("startTime", "12:00"),
        "start_date": start_date,
        "endTime": slot.get("endTime", "12:20"),
        "resourceid": slot.get("resourceid", " ")
    }
    
    # Encabezados
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Cookie": "lang=es",
        "Content-Type": "application/json"
    }
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        # Intentar obtener la respuesta JSON incluso si hay error HTTP
        try:
            data = response.json()
        except:
            data = {"result": "ERROR", "error": "No se pudo decodificar la respuesta JSON"}
        
        print(f"\nCódigo de respuesta: {response.status_code}")
        print(f"Resultado: {data.get('result', 'N/A')}")
        
        # Guardar la respuesta completa en un archivo para análisis
        with open("reservation_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Respuesta completa guardada en 'reservation_response.json'")
        
        if response.status_code == 200 and data.get("result") == "OK":
            print("\n¡Reserva realizada con éxito!")
            print(f"ID de reserva: {data.get('return', {}).get('reservationid', 'N/A')}")
            return data
        else:
            print(f"\nError al realizar la reserva: {data.get('error', 'Error desconocido')}")
            print("Detalles de la respuesta:")
            print(json.dumps(data, indent=2))
            return None
            
    except Exception as e:
        print(f"Error al realizar la reserva: {str(e)}")
        return None

def main():
    """Función principal que ejecuta la secuencia completa de pruebas"""
    print("=== PRUEBA DE SECUENCIA COMPLETA DE RESERVA EN TUOTEMPO ===")
    print(f"Fecha y hora de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL base: {BASE_URL}/{INSTANCE_ID}")
    print(f"ID de actividad: {ACTIVITY_ID}")
    print(f"Fecha de inicio: {START_DATE}")
    print(f"Usuario: {FNAME} {LNAME}")
    print(f"Teléfono: {PHONE}")
    
    # Paso 1: Obtener disponibilidades - intentar con diferentes clínicas y fechas
    selected_slot = None
    current_date = START_DATE
    
    # Probar con cada clínica
    for clinic_index, clinic_id in enumerate(CLINICS):
        print(f"\nProbando con clínica {clinic_index + 1}: {clinic_id}")
        
        # Intentar hasta 4 semanas si no hay disponibilidad
        for attempt in range(4):
            if attempt > 0:
                # Convertir la fecha a objeto datetime para sumar 7 días
                date_parts = current_date.split('-')
                date_obj = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                date_obj += timedelta(days=7)
                current_date = date_obj.strftime('%d-%m-%Y')
                print(f"\nIntentando con la siguiente semana: {current_date}")
            
            selected_slot = get_availabilities(current_date, clinic_id)
            if selected_slot:
                print(f"\n¡Disponibilidad encontrada en clínica {clinic_index + 1}!")
                break
        
        if selected_slot:
            break
        else:
            # Reiniciar la fecha para la siguiente clínica
            current_date = START_DATE
    
    if not selected_slot:
        print("\nNo se encontraron disponibilidades en ninguna clínica en las próximas 4 semanas.")
        sys.exit(1)
    
    # Paso 2: Registrar usuario
    user_id = register_user()
    
    if not user_id:
        print("\nNo se puede continuar sin un usuario registrado.")
        sys.exit(1)
    
    # Paso 3: Realizar reserva
    reservation = make_reservation(user_id, selected_slot)
    
    print_separator()
    if reservation:
        print("✅ PRUEBA COMPLETADA CON ÉXITO")
    else:
        print("❌ LA PRUEBA FALLÓ EN ALGÚN PUNTO")
    
    print("\nRevise los archivos JSON generados para más detalles:")
    print("- availabilities_response.json")
    print("- user_registration_response.json")
    print("- reservation_response.json")

if __name__ == "__main__":
    main()

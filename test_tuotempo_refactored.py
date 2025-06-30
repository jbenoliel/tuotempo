#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para probar la secuencia completa de reserva de citas en TuoTempo
utilizando la clase TuoTempoAPI.
1. Itera sobre una lista de clínicas.
2. Para cada clínica, busca disponibilidad en las próximas 4 semanas.
3. Si encuentra un hueco, registra al usuario.
4. Finalmente, confirma la reserva.
"""

import sys
import json

print("--- SCRIPT EJECUTÁNDOSE ---")
from datetime import datetime, timedelta
from tuotempo_api import TuoTempoAPI

# --- CONFIGURACIÓN DE LA PRUEBA ---

# ID de actividad para "Primera Visita Odontología General"
ACTIVITY_ID = "sc159232371eb9c1"

# Lista de clínicas para probar (reemplazar con los IDs correctos si son diferentes)
CLINIC_IDS = [
    "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44kowswy_sejh",
    "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_454owswy_sejh",
    "default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_4cbowswy_sejh"
]

# Fecha de inicio para la búsqueda
START_DATE = "10-07-2025"  # Formato DD-MM-YYYY

# Datos del usuario para el registro
USER_DATA = {
    "fname": "Jacques",
    "lname": "Benoliel",
    "phone": "+34629203315",
    "birthday": "17/10/1961"  # Formato DD/MM/YYYY
}

# --- FIN DE LA CONFIGURACIÓN ---

def print_separator():
    """Imprime una línea separadora para mejorar la legibilidad."""
    print("\n" + "="*80 + "\n")

def save_json_response(filename, data):
    """Guarda la respuesta JSON en un archivo para depuración."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"-> Respuesta guardada en '{filename}'")
    except Exception as e:
        print(f"Error al guardar el archivo JSON: {e}")

def main():
    """Función principal que ejecuta la secuencia completa de pruebas."""
    print("=== INICIANDO PRUEBA COMPLETA DE RESERVA EN TUOTEMPO ===")
    
    # Inicializar el cliente de la API (cambiar a "PRE" si es necesario)
    api = TuoTempoAPI(environment="PRO")
    print(f"Entorno de API: {api.environment}")
    print_separator()

    # --- PASO 1: BÚSQUEDA DE DISPONIBILIDAD ---
    selected_slot = None
    search_date_obj = datetime.strptime(START_DATE, "%d-%m-%Y")

    for clinic_id in CLINIC_IDS:
        print(f"Buscando en la clínica: {clinic_id}")
        current_search_date = search_date_obj

        for week in range(4):  # Intentar por 4 semanas
            date_str = current_search_date.strftime("%d-%m-%Y")
            print(f"\nIntentando buscar a partir de la fecha: {date_str}")
            
            response = api.get_available_slots(ACTIVITY_ID, clinic_id, date_str)
            clinic_unique_id = clinic_id.split('_')[-2]
            save_json_response(f"availabilities_{clinic_unique_id}_{date_str}.json", response)

            if response and response.get("result") == "OK":
                availabilities = response.get("return", {}).get("results", {}).get("availabilities", [])
                if availabilities:
                    selected_slot = availabilities[0]
                    print(f"\n¡Disponibilidad encontrada en la clínica {clinic_id}!")
                    print(f"Slot seleccionado: {selected_slot.get('start_date')} de {selected_slot.get('startTime')} a {selected_slot.get('endTime')}")
                    break
            
            current_search_date += timedelta(days=7)
        
        if selected_slot:
            break

    if not selected_slot:
        print_separator()
        print("\nError: No se encontró disponibilidad en ninguna de las clínicas y fechas probadas.")
        sys.exit(1)

    print_separator()

    # --- PASO 2: REGISTRO DE USUARIO ---
    print("PASO 2: Registrando usuario no asegurado...")
    user_response = api.register_non_insured_user(**USER_DATA)
    save_json_response("user_registration.json", user_response)

    member_id = None
    if user_response.get("access_token"):
        member_id = user_response.get("user_info", {}).get("memberid")
        api.session_id = user_response.get("user_info", {}).get("sessionid")
    elif user_response.get("result") == "OK":
        member_id = user_response.get("return", {}).get("memberid")
    else:
        error_msg = user_response.get("msg") or user_response.get("error", "Error desconocido")
        print(f"\nError al registrar el usuario: {error_msg}")
        sys.exit(1)

    if not member_id:
        print("\nError: El registro se completó pero no se devolvió 'memberid'.")
        sys.exit(1)

    print(f"Usuario registrado con éxito. MemberID: {member_id}")

    print_separator()
    # después de registrar al usuario
    member_id = user_response["user_info"]["memberid"]
    api.session_id = member_id          # <<< usar memberid, no sessionid

    # --- PASO 3: CONFIRMACIÓN DE RESERVA ---
    print("PASO 3: Confirmando la reserva...")
    
    # Confirmar la reserva directamente con el slot completo
    reservation_response = api.confirm_appointment(selected_slot, USER_DATA['phone'])
    save_json_response("reservation_confirmation.json", reservation_response)

    # Convertir a dict si la API devuelve una cadena
    if isinstance(reservation_response, str):
        try:
            reservation_response = json.loads(reservation_response)
        except json.JSONDecodeError:
            print(f"\nLa API devolvió texto plano: {reservation_response}")
            sys.exit(1)

    if not isinstance(reservation_response, dict):
        print(f"\nRespuesta inesperada de /reservations: {reservation_response}")
        sys.exit(1)

    if reservation_response.get("result") == "OK":
        # El campo 'return' contiene directamente el ID de la reserva como string
        reservation_id = reservation_response.get("return")
        print("\n¡RESERVA CONFIRMADA CON ÉXITO!")
        print(f"ID de la reserva: {reservation_id}")
        print(f"Mensaje: {reservation_response.get('msg', '')}")
    else:
        error_msg = reservation_response.get("msg") or reservation_response.get("error", "Error desconocido")
        print(f"\nError al confirmar la reserva: {error_msg}")
        sys.exit(1)

    print_separator()
    print("✅ PRUEBA COMPLETADA CON ÉXITO")

if __name__ == "__main__":
    main()

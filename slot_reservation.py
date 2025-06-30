#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
import requests
from datetime import datetime

class TuoTempoSlotReservation:
    """
    Clase simplificada para reservar un slot específico en TuoTempo
    cuando ya se tienen los slots en formato texto
    """
    
    def __init__(self, api_key=None, instance_id=None, environment="PRO"):
        # Default API keys for VOICEBOT2
        pre_key = "3a5835be0f540c7591c754a2bf0758bb"  # PRE environment
        pro_key = "24b98d8d41b970d38362b52bd3505c04"  # PRO environment
        
        self.api_key = api_key or (pre_key if environment == "PRE" else pro_key)
        self.instance_id = instance_id or "tt_portal_adeslas"
        self.base_url = f"https://app.tuotempo.com/api/v3/{self.instance_id}"
    
    def make_reservation(self, slots_json_list, selected_date, selected_time, userid, phone):
        """
        Reserva un slot específico a partir de slots en formato texto
        
        Args:
            slots_json_list (list): Lista de 3 slots en formato JSON (como texto)
            selected_date (str): Fecha seleccionada en formato DD/MM/YYYY
            selected_time (str): Hora seleccionada en formato HH:MM
            userid (str): ID de usuario registrado
            phone (str): Teléfono de contacto
            
        Returns:
            dict: Respuesta de la API
        """
        # Buscamos el slot que coincide con la fecha y hora seleccionadas
        selected_slot = None
        
        for slot_json in slots_json_list:
            try:
                slot = json.loads(slot_json)
                if (slot.get("start_date") == selected_date and 
                    slot.get("startTime") == selected_time):
                    selected_slot = slot
                    break
            except json.JSONDecodeError:
                print(f"Error decodificando slot JSON: {slot_json[:100]}...")
                continue
        
        if not selected_slot:
            return {
                "result": "ERROR", 
                "msg": f"No se encontró slot para fecha {selected_date} y hora {selected_time}"
            }
        
        # Añadimos la información del usuario al slot
        selected_slot["userid"] = userid
        selected_slot["communication_phone"] = phone
        selected_slot["tags"] = "WEB_NO_ASEGURADO"
        selected_slot["isExternalPayment"] = "false"
        
        # Hacemos la petición a la API
        url = f"{self.base_url}/reservations"
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'Authorization': f'Bearer {self.api_key}'
        }
        params = {'lang': 'es'}
        
        # Debug
        print("\n=== DEBUG /reservations ===")
        print(f"URL: {url}")
        print(f"Params: {params}")
        print(f"Headers: {headers}")
        print("Payload:")
        print(json.dumps(selected_slot, ensure_ascii=False, indent=2)[:500] + "..." if len(json.dumps(selected_slot)) > 500 else json.dumps(selected_slot, ensure_ascii=False, indent=2))
        print("===========================\n")
        
        response = requests.post(url, headers=headers, params=params, json=selected_slot)
        
        # Debug respuesta
        print("\n=== DEBUG RESPUESTA /reservations ===")
        print(f"Status code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        content_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
        print(f"Contenido: {content_preview}")
        print("===========================\n")
        
        try:
            result = response.json()
            # Si la reserva fue exitosa, añadimos información para facilidad de uso
            if result.get("result") == "OK":
                reservation_id = result.get("return")
                print("\n¡RESERVA CONFIRMADA CON ÉXITO!")
                print(f"ID de la reserva: {reservation_id}")
                print(f"Mensaje: {result.get('msg', '')}")
            return result
        except json.JSONDecodeError:
            print(f"Error decodificando respuesta: {response.text[:200]}...")
            return {"result": "ERROR", "msg": "Error decodificando respuesta", "response_text": response.text}


def main():
    """Función principal para probar el script"""
    import argparse
    
    # Configuración de argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Reserva un slot específico en TuoTempo')
    parser.add_argument('--api-key', required=False, help='API key de TuoTempo (opcional, usa valor predeterminado si no se proporciona)')
    parser.add_argument('--instance-id', required=False, help='ID de instancia de TuoTempo (ej: tt_portal_adeslas)')
    parser.add_argument('--environment', default='PRO', choices=['PRE', 'PRO'], help='Entorno a utilizar (PRE o PRO, por defecto PRO)')
    parser.add_argument('--userid', required=True, help='ID del usuario ya registrado')
    parser.add_argument('--phone', required=True, help='Teléfono de contacto')
    parser.add_argument('--date', required=True, help='Fecha seleccionada (DD/MM/YYYY)')
    parser.add_argument('--time', required=True, help='Hora seleccionada (HH:MM)')
    parser.add_argument('--slots', required=False, nargs='+', help='JSONs de slots (entre comillas)')
    parser.add_argument('--slots-file', help='Archivo JSON con lista de slots')
    parser.add_argument('--simple-slot', nargs=5, help='Formato simple de slot: start_date startTime endTime resourceid areaid')
    
    args = parser.parse_args()
    
    # Usar valores de los argumentos
    api_key = args.api_key  # Puede ser None
    instance_id = args.instance_id  # Puede ser None
    environment = args.environment  # 'PRE' o 'PRO'
    userid = args.userid
    phone = args.phone
    selected_date = args.date
    selected_time = args.time
    
    # Procesamiento de slots en diferentes formatos
    slots_json_list = []
    
    # 1. Si se proporciona --slots-file
    if args.slots_file:
        try:
            with open(args.slots_file, 'r', encoding='utf-8') as f:
                slots_data = json.load(f)
                if isinstance(slots_data, list):
                    slots_json_list = [json.dumps(slot) for slot in slots_data]
                else:
                    slots_json_list = [json.dumps(slots_data)]
        except Exception as e:
            print(f"Error al leer archivo de slots: {e}")
            sys.exit(1)
    
    # 2. Si se proporciona --simple-slot
    elif args.simple_slot:
        try:
            start_date, start_time, end_time, resourceid, areaid = args.simple_slot
            simple_slot = {
                "start_date": start_date,
                "startTime": start_time,
                "endTime": end_time,
                "resourceid": resourceid,
                "areaid": areaid
            }
            slots_json_list = [json.dumps(simple_slot)]
        except Exception as e:
            print(f"Error al procesar slot simple: {e}")
            sys.exit(1)
    
    # 3. Si se proporcionan --slots
    elif args.slots:
        slots_json_list = args.slots
    
    # Si no hay slots, error
    if not slots_json_list:
        print("Error: Debe proporcionar slots usando --slots, --slots-file o --simple-slot")
        sys.exit(1)
    
    print(f"Reservando para fecha: {selected_date} a las {selected_time}")
    print(f"Usuario ID: {userid}")
    print(f"Teléfono: {phone}")
    print(f"Entorno: {environment}")
    print(f"Instancia: {instance_id or 'tt_portal_adeslas (predeterminada)'}")
    print(f"API Key: {api_key or '(usando clave predeterminada)'}")
    print(f"Procesando {len(slots_json_list)} slots...")
    
    # Mostramos resumen de los slots recibidos
    for i, slot_json in enumerate(slots_json_list):
        try:
            slot = json.loads(slot_json)
            print(f"Slot {i+1}: {slot.get('start_date')} {slot.get('startTime')}-{slot.get('endTime')}")
        except json.JSONDecodeError:
            print(f"Error en slot {i+1}: JSON inválido")
            print(slot_json[:50] + "..." if len(slot_json) > 50 else slot_json)
    
    # Crear instancia y hacer la reserva
    reservation = TuoTempoSlotReservation(api_key=api_key, instance_id=instance_id, environment=environment)
    result = reservation.make_reservation(slots_json_list, selected_date, selected_time, userid, phone)
    
    # Guardar resultado en archivo JSON para referencia
    with open('slot_reservation_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\nResultado guardado en 'slot_reservation_result.json'")
    

if __name__ == "__main__":
    main()

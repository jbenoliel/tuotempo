#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

class TuoTempoSlotReservation:
    """
    Clase simplificada para reservar un slot específico en TuoTempo
    """
    
    def __init__(self, api_key=None, instance_id=None, environment="PRO"):
        # Default API keys for VOICEBOT2
        pre_key = "3a5835be0f540c7591c754a2bf0758bb"  # PRE environment
        pro_key = "24b98d8d41b970d38362b52bd3505c04"  # PRO environment
        
        self.api_key = api_key or (pre_key if environment == "PRE" else pro_key)
        self.instance_id = instance_id or "tt_portal_adeslas"
        self.base_url = f"https://app.tuotempo.com/api/v3/{self.instance_id}"
    
    def make_reservation(self, slot_data, userid, phone, selected_date=None, selected_time=None):
        """
        Reserva un slot específico
        
        Args:
            slot_data (dict): Datos del slot a reservar
            userid (str): ID de usuario registrado
            phone (str): Teléfono de contacto
            selected_date (str, optional): Fecha seleccionada (DD/MM/YYYY). Si se proporciona, se verificará
            selected_time (str, optional): Hora seleccionada (HH:MM). Si se proporciona, se verificará
            
        Returns:
            dict: Respuesta de la API
        """
        # Si se especificaron fecha y hora, verificamos que coincidan con el slot
        if selected_date and selected_time:
            if slot_data.get("start_date") != selected_date or slot_data.get("startTime") != selected_time:
                return {
                    "result": "ERROR",
                    "msg": f"El slot proporcionado no coincide con la fecha {selected_date} y hora {selected_time} seleccionadas"
                }
        
        # Añadimos la información del usuario al slot
        slot_data["userid"] = userid
        slot_data["communication_phone"] = phone
        slot_data["tags"] = "WEB_NO_ASEGURADO"
        slot_data["isExternalPayment"] = "false"
        
        # Hacemos la petición a la API
        url = f"{self.base_url}/reservations"
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'Authorization': f'Bearer {self.api_key}'
        }
        params = {'lang': 'es'}
        
        # Debug
        app.logger.info(f"URL: {url}")
        app.logger.info(f"Params: {params}")
        app.logger.info(f"Headers: {headers}")
        app.logger.info(f"Payload: {json.dumps(slot_data, ensure_ascii=False)[:500]}...")
        
        response = requests.post(url, headers=headers, params=params, json=slot_data)
        
        # Debug respuesta
        app.logger.info(f"Status code: {response.status_code}")
        app.logger.info(f"Headers: {dict(response.headers)}")
        app.logger.info(f"Contenido: {response.text[:500]}...")
        
        try:
            result = response.json()
            return result
        except json.JSONDecodeError:
            app.logger.error(f"Error decodificando respuesta: {response.text[:200]}...")
            return {"result": "ERROR", "msg": "Error decodificando respuesta", "response_text": response.text}


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "ok",
        "version": "1.0.0"
    }), 200


@app.route('/reserve', methods=['POST'])
def reserve_slot():
    """Endpoint para reservar un slot"""
    try:
        data = request.json
        
        # Validar campos requeridos
        required_fields = ['userid', 'phone', 'slot']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "result": "ERROR",
                    "msg": f"Campo requerido no proporcionado: {field}"
                }), 400
        
        # Extraer datos
        userid = data['userid']
        phone = data['phone']
        slot_data = data['slot']
        date = data.get('date')  # Opcional
        time = data.get('time')  # Opcional
        api_key = data.get('api_key')  # Opcional
        instance_id = data.get('instance_id')  # Opcional
        environment = data.get('environment', 'PRO')  # Opcional, default PRO
        
        # Validar datos mínimos del slot
        required_slot_fields = ['start_date', 'startTime', 'endTime', 'resourceid', 'areaid']
        for field in required_slot_fields:
            if field not in slot_data:
                return jsonify({
                    "result": "ERROR",
                    "msg": f"Campo requerido no proporcionado en slot: {field}"
                }), 400
        
        # Inicializar cliente y hacer reserva
        reservation = TuoTempoSlotReservation(
            api_key=api_key, 
            instance_id=instance_id,
            environment=environment
        )
        
        result = reservation.make_reservation(
            slot_data=slot_data,
            userid=userid,
            phone=phone,
            selected_date=date,
            selected_time=time
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        app.logger.error(f"Error al procesar la reserva: {str(e)}")
        return jsonify({
            "result": "ERROR",
            "msg": f"Error al procesar la reserva: {str(e)}"
        }), 500


if __name__ == '__main__':
    # Configuración para producción
    import argparse
    
    parser = argparse.ArgumentParser(description='API REST para reservas en TuoTempo')
    parser.add_argument('--host', default='0.0.0.0', help='Host para el servidor')
    parser.add_argument('--port', type=int, default=5000, help='Puerto para el servidor')
    parser.add_argument('--debug', action='store_true', help='Activar modo debug')
    
    args = parser.parse_args()
    
    # Configurar logging
    import logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    print(f"Iniciando API en http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

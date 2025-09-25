import os
import logging
import requests
import json
from dotenv import load_dotenv
from tuotempo_api_logger import log_tuotempo_api_call

# Load environment variables
load_dotenv()

class Tuotempo:
    """
    Clase adaptadora para mantener compatibilidad con el código existente.
    Esta clase traduce las llamadas del formato nuevo al formato que usa TuoTempoAPI.
    """
    
    def __init__(self, api_key, api_secret, instance_id):
        """
        Inicializa el cliente Tuotempo.
        
        Args:
            api_key (str): Clave API para autenticación.
            api_secret (str): No usado actualmente, mantenido por compatibilidad.
            instance_id (str): ID de la instancia de TuoTempo.
        """
        self.api_key = api_key
        self.instance_id = instance_id
        # Determinar el environment basado en la key
        is_pro = any(pro_key in api_key for pro_key in ['PRO', 'pro'])
        self.environment = "PRO" if is_pro else "PRE"
        
        # Importar TuoTempoAPI aquí para evitar importación circular
        from tuotempo_api import TuoTempoAPI
        
        # Inicializar el cliente real
        self.client = TuoTempoAPI(
            instance_id=instance_id,
            api_key=api_key,
            environment=self.environment
        )
        
        logging.info(f"Tuotempo adapter initialized for {self.environment} environment")
    
    @log_tuotempo_api_call
    def get_available_slots(self, locations_lid, start_date, days=7):
        """
        Obtiene slots disponibles para la ubicación y fecha especificadas.
        
        Args:
            locations_lid (list): Lista de IDs de centros.
            start_date (str): Fecha de inicio en formato DD-MM-YYYY.
            days (int): Número de días a considerar.
            
        Returns:
            dict: Respuesta con los slots disponibles.
        """
        # Convertir de formato DD-MM-YYYY a DD/MM/YYYY que usa TuoTempoAPI
        if start_date and '-' in start_date:
            start_date = start_date.replace('-', '/')
        
        # Obtener el ID de la actividad (en una implementación real, esto debería ser configurable)
        activity_id = os.getenv('TUOTEMPO_ACTIVITY_ID', 'sc159232371eb9c1')
        
        # Simplificar a un solo centro si es una lista
        area_id = locations_lid[0] if isinstance(locations_lid, list) and locations_lid else locations_lid
        
        logging.info(f"Adapter: buscando slots para area_id={area_id}, start_date={start_date}")
        
        # Llamar al método correspondiente de TuoTempoAPI
        try:
            return self.client.get_available_slots(
                activity_id=activity_id, 
                area_id=area_id, 
                start_date=start_date,
                time_preference='MORNING'  # Valor por defecto para evitar error de preferenciaMT vacía
            )
        except Exception as e:
            logging.error(f"Error al obtener slots: {e}")
            return {"error": str(e)}
    
    @log_tuotempo_api_call
    def create_reservation(self, user_info, availability):
        """
        Crea una reserva con la información proporcionada.
        
        Args:
            user_info (dict): Información del usuario con name, surname, birth_date, mobile_phone.
            availability (dict): Información de disponibilidad con start_date, startTime, endTime, resourceid, activityid.
            
        Returns:
            dict: Respuesta de la reserva.
        """
        logging.info(f"Adapter: creando reserva para {user_info.get('name')} en {availability.get('start_date')}")
        
        try:
            # Primero registrar al usuario
            user_reg_response = self.client.register_non_insured_user(
                fname=user_info.get('name'),
                lname=user_info.get('surname'),
                birthday=user_info.get('birth_date'),
                phone=user_info.get('mobile_phone')
            )
            
            # Si no hay session_id después del registro, falló
            if not self.client.session_id:
                return {
                    "result": "ERROR",
                    "msg": "No se pudo registrar el usuario",
                    "details": user_reg_response
                }
            
            # Adaptar el formato de la fecha si es necesario
            start_date = availability.get('start_date')
            if start_date and '-' in start_date:
                start_date = start_date.replace('-', '/')
            
            # Confirmar la cita
            confirm_response = self.client.confirm_appointment(
                availability={
                    "start_date": start_date,
                    "startTime": availability.get('startTime'),
                    "endTime": availability.get('endTime'),
                    "resourceid": availability.get('resourceid'),
                    "activityid": availability.get('activityid')
                },
                communication_phone=user_info.get('mobile_phone')
            )
            
            # Si la respuesta indica éxito
            if confirm_response.get("result") == "OK":
                return confirm_response
            else:
                return {
                    "result": "ERROR",
                    "msg": "No se pudo confirmar la cita",
                    "details": confirm_response
                }
        except Exception as e:
            logging.exception("Error en create_reservation")
            return {
                "result": "ERROR",
                "msg": str(e)
            }

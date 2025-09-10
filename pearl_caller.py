"""
Módulo para integración con la API de Pearl AI (NLPearl).
Maneja la autenticación, obtención de outbound IDs y realización de llamadas.
"""

import os
import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PearlAPIError(Exception):
    """Excepción personalizada para errores de la API de Pearl."""
    pass

class PearlCaller:
    """Clase para gestionar llamadas automáticas a través de la API de Pearl AI."""
    
    def __init__(self):
        """Inicializa el cliente de Pearl AI con credenciales desde variables de entorno."""
        self.account_id = os.getenv('PEARL_ACCOUNT_ID')
        self.secret_key = os.getenv('PEARL_SECRET_KEY')
        self.api_url = os.getenv('PEARL_API_URL', 'https://api.nlpearl.ai/v1')
        self.default_outbound_id = os.getenv('PEARL_OUTBOUND_ID')
        
        # Validar credenciales
        if not self.account_id or not self.secret_key:
            raise PearlAPIError(
                "Credenciales de Pearl AI no configuradas. "
                "Asegúrate de definir PEARL_ACCOUNT_ID y PEARL_SECRET_KEY en .env"
            )
        
        # Configurar headers de autenticación
        self.headers = {
            "Authorization": f"Bearer {self.account_id}:{self.secret_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("Cliente Pearl AI inicializado correctamente")
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión con la API de Pearl AI.
        
        Returns:
            bool: True si la conexión es exitosa, False en caso contrario
        """
        try:
            response = requests.get(
                f"{self.api_url}/Outbound",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Conexión con Pearl AI exitosa")
                return True
            else:
                logger.error(f"❌ Error de conexión: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al probar conexión: {str(e)}")
            return False
    
    def get_outbound_campaigns(self) -> List[Dict]:
        """
        Obtiene la lista de campañas outbound disponibles.
        
        Returns:
            List[Dict]: Lista de campañas outbound
            
        Raises:
            PearlAPIError: Si hay error en la API
        """
        try:
            logger.info("Obteniendo campañas outbound...")
            response = requests.get(
                f"{self.api_url}/Outbound",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                campaigns = response.json()
                logger.info(f"✅ Obtenidas {len(campaigns)} campañas outbound")
                return campaigns
            else:
                error_msg = f"Error al obtener campañas: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PearlAPIError(error_msg)
                
        except requests.RequestException as e:
            error_msg = f"Error de conexión al obtener campañas: {str(e)}"
            logger.error(error_msg)
            raise PearlAPIError(error_msg)
    
    def get_outbound_details(self, outbound_id: str) -> Dict:
        """
        Obtiene los detalles de una campaña outbound específica.
        
        Args:
            outbound_id (str): ID de la campaña outbound
            
        Returns:
            Dict: Detalles de la campaña
            
        Raises:
            PearlAPIError: Si hay error en la API
        """
        try:
            logger.info(f"Obteniendo detalles de outbound ID: {outbound_id}")
            response = requests.get(
                f"{self.api_url}/Outbound/{outbound_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                details = response.json()
                logger.info(f"✅ Detalles obtenidos para outbound {outbound_id}")
                return details
            else:
                error_msg = f"Error al obtener detalles: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PearlAPIError(error_msg)
                
        except requests.RequestException as e:
            error_msg = f"Error de conexión al obtener detalles: {str(e)}"
            logger.error(error_msg)
            raise PearlAPIError(error_msg)
    
    def make_call(self, outbound_id: str, phone_number: str, lead_data: Dict) -> Tuple[bool, Dict]:
        """
        Realiza una llamada automática usando la API de Pearl.
        
        Args:
            outbound_id (str): ID de la campaña outbound
            phone_number (str): Número de teléfono a llamar
            lead_data (Dict): Datos del lead para personalizar la llamada
            
        Returns:
            Tuple[bool, Dict]: (éxito, respuesta_de_api)
            
        Raises:
            PearlAPIError: Si hay error en la API
        """
        try:
            # Determinar el saludo según la hora
            greeting = "Buenos días" if datetime.now().hour < 14 else "Buenas tardes"

            # Construir el objeto callData
            call_data_payload = {
                "certificado": lead_data.get('certificado', ''),
                "clinicaId": lead_data.get('clinica_id', ''),
                "codigoPostal": lead_data.get('codigo_postal', ''),
                "delegacion": lead_data.get('delegacion', ''),
                "dias_tardes": greeting,
                "direccionClinica": lead_data.get('direccion_clinica', ''),
                "emailAddress": lead_data.get('email', ''),
                "fechaNacimiento": str(lead_data.get('fecha_nacimiento', '')),
                "firstName": lead_data.get('nombre', ''),
                "lastName": lead_data.get('apellidos', ''),
                "nif": lead_data.get('nif', ''),
                "nombreClinica": lead_data.get('nombre_clinica', ''),
                "orden": lead_data.get('orden'),
                "poliza": lead_data.get('poliza', ''),
                "segmento": lead_data.get('segmento', ''),
                "sexo": lead_data.get('sexo', '')
            }
            
            # Preparar el payload final de la llamada
            call_payload = {
                "to": phone_number,
                "callData": call_data_payload
            }
            
            logger.info(f"🚀 INICIANDO LLAMADA A PEARL AI")
            logger.info(f"📞 Número de teléfono: {phone_number}")
            logger.info(f"🏥 Lead: {lead_data.get('nombre', 'N/A')} {lead_data.get('apellidos', 'N/A')}")
            logger.info(f"🆔 Outbound ID: {outbound_id}")
            logger.info(f"🌐 URL de Pearl: {self.api_url}/Outbound/{outbound_id}/Call")
            logger.debug(f"📦 Payload completo: {json.dumps(call_payload, indent=2)}")
            
            url = f"{self.api_url}/Outbound/{outbound_id}/Call"
            response = requests.post(url, headers=self.headers, json=call_payload, timeout=30)
            
            response_data = {}
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}

            if response.status_code == 200:
                logger.info(f"✅ Llamada iniciada exitosamente a {phone_number}")
                logger.debug(f"Respuesta: {json.dumps(response_data, indent=2)}")
                return True, response_data
            else:
                error_msg = f"Error al hacer llamada: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, response_data

        except requests.RequestException as e:
            error_msg = f"Error de conexión al hacer llamada: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}

    def search_calls(self, outbound_id: str, from_date: str, to_date: str) -> List[Dict]:
        """
        Busca llamadas en un rango de fechas para una campaña outbound.

        Args:
            outbound_id (str): ID de la campaña outbound.
            from_date (str): Fecha de inicio (formato YYYY-MM-DDTHH:MM:SSZ).
            to_date (str): Fecha de fin (formato YYYY-MM-DDTHH:MM:SSZ).

        Returns:
            List[Dict]: Lista de llamadas encontradas.

        Raises:
            PearlAPIError: Si ocurre un error en la llamada a la API.
        """
        try:
            search_payload = {
                "fromDate": from_date,
                "toDate": to_date,
                "limit": 100  # Máximo permitido por Pearl AI
            }
            logger.info(f"Buscando llamadas para outbound {outbound_id} de {from_date} a {to_date}")
            response = requests.post(
                f"{self.api_url}/Outbound/{outbound_id}/Calls",
                headers=self.headers,
                json=search_payload,
                timeout=60
            )

            if response.status_code == 200:
                calls = response.json()
                call_count = calls.get('count', 0) if isinstance(calls, dict) else len(calls)
                logger.info(f"✅ Encontradas {call_count} llamadas.")
                return calls
            else:
                error_msg = f"Error al buscar llamadas: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PearlAPIError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Error de conexión al buscar llamadas: {str(e)}"
            logger.error(error_msg)
            raise PearlAPIError(error_msg)

    def search_calls_paginated(self, outbound_id: str, from_date: str, to_date: str, skip: int = 0, limit: int = 100) -> List[Dict]:
        """
        Busca llamadas con paginación.
        """
        try:
            search_payload = {
                "fromDate": from_date,
                "toDate": to_date,
                "skip": skip,
                "limit": limit
            }
            response = requests.post(
                f"{self.api_url}/Outbound/{outbound_id}/Calls",
                headers=self.headers,
                json=search_payload,
                timeout=60
            )

            if response.status_code == 200:
                calls = response.json()
                return calls
            else:
                error_msg = f"Error al buscar llamadas paginadas: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PearlAPIError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Error de conexión al buscar llamadas paginadas: {str(e)}"
            logger.error(error_msg)
            raise PearlAPIError(error_msg)

    def get_call_status(self, call_id: str) -> Dict:
        """
        Obtiene el estado y los detalles de una llamada específica.

        Args:
            call_id (str): ID de la llamada

        Returns:
            Dict: Estado y detalles de la llamada

        Raises:
            PearlAPIError: Si hay error en la API
        """
        try:
            logger.info(f"Obteniendo estado de llamada: {call_id}")
            response = requests.get(
                f"{self.api_url}/Call/{call_id}",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                call_data = response.json()
                logger.info(f"✅ Estado obtenido para llamada {call_id}")
                return call_data
            else:
                error_msg = f"Error al obtener estado: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PearlAPIError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Error de conexión al obtener estado: {str(e)}"
            logger.error(error_msg)
            raise PearlAPIError(error_msg)
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Valida formato básico del número de teléfono.
        
        Args:
            phone_number (str): Número a validar
            
        Returns:
            bool: True si es válido, False en caso contrario
        """
        if not phone_number:
            return False
        
        # Limpiar el número
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Validar longitud (entre 9 y 15 dígitos)
        if len(clean_number) < 9 or len(clean_number) > 15:
            return False
        
        # Validar que no sean todos ceros
        if clean_number == '0' * len(clean_number):
            return False
        
        return True
    
    def format_phone_number(self, phone_number: str, country_code: str = "+34") -> str:
        """
        Formatea un número de teléfono para uso internacional.
        
        Args:
            phone_number (str): Número original
            country_code (str): Código de país (por defecto +34 para España)
            
        Returns:
            str: Número formateado
        """
        if not phone_number:
            return ""
        
        # Limpiar el número
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Si ya tiene código de país, devolverlo limpio
        if clean_number.startswith('34') and len(clean_number) > 9:
            return f"+{clean_number}"
        
        # Si es un número español de 9 dígitos, añadir +34
        if len(clean_number) == 9:
            return f"{country_code}{clean_number}"
        
        # En otros casos, devolver con + si no lo tiene
        if not phone_number.startswith('+'):
            return f"+{clean_number}"
        
        return phone_number
    
    def get_default_outbound_id(self) -> Optional[str]:
        """
        Obtiene el outbound ID por defecto configurado.
        
        Returns:
            Optional[str]: Outbound ID por defecto o None si no está configurado
        """
        return self.default_outbound_id
    
    def log_call_attempt(self, lead_id: int, phone_number: str, success: bool, response: Dict):
        """
        Registra un intento de llamada para logging y debug.
        
        Args:
            lead_id (int): ID del lead
            phone_number (str): Número llamado
            success (bool): Si la llamada fue exitosa
            response (Dict): Respuesta de la API
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "lead_id": lead_id,
            "phone_number": phone_number,
            "success": success,
            "response": response
        }
        
        if success:
            logger.info(f"📞 Llamada exitosa - Lead {lead_id}: {phone_number}")
        else:
            logger.warning(f"⚠️ Llamada fallida - Lead {lead_id}: {phone_number}")
            logger.debug(f"Error details: {json.dumps(response, indent=2)}")
            
    def validate_phone_number(self, phone: str) -> bool:
        """
        Valida si un número de teléfono tiene el formato correcto para realizar llamadas.
        
        Args:
            phone (str): Número de teléfono a validar
            
        Returns:
            bool: True si el teléfono es válido, False en caso contrario
        """
        if not phone:
            return False
            
        # Eliminar espacios, guiones y otros caracteres no numéricos
        digits = ''.join(c for c in phone if c.isdigit())
        
        # Verificar longitud mínima (al menos 9 dígitos para España)
        if len(digits) < 9:
            logger.debug(f"Teléfono inválido (muy corto): {phone}")
            return False
            
        # Si tiene prefijo internacional con +, validar
        if phone.startswith('+'):
            # Comprobar que es un prefijo válido
            if not (phone.startswith('+34') or phone.startswith('+1') or 
                    phone.startswith('+44') or phone.startswith('+52')):
                logger.debug(f"Prefijo internacional no soportado: {phone}")
                return False
        
        # Reglas específicas para España
        if len(digits) == 9 and not (digits.startswith('6') or 
                                   digits.startswith('7') or 
                                   digits.startswith('8') or 
                                   digits.startswith('9')):
            logger.debug(f"Teléfono español inválido: {phone}")
            return False
            
        logger.debug(f"Teléfono validado: {phone}")
        return True

# Instancia global del cliente (singleton pattern)
_pearl_client = None

def get_pearl_client() -> PearlCaller:
    """
    Obtiene una instancia singleton del cliente Pearl AI.
    
    Returns:
        PearlCaller: Cliente configurado
    """
    global _pearl_client
    if _pearl_client is None:
        _pearl_client = PearlCaller()
    return _pearl_client

# Funciones de utilidad para usar directamente
def test_pearl_connection() -> bool:
    """Prueba rápida de conexión con Pearl AI."""
    try:
        client = get_pearl_client()
        return client.test_connection()
    except Exception as e:
        logger.error(f"Error al probar conexión: {e}")
        return False

def make_pearl_call(outbound_id: str, phone_number: str, lead_data: Dict) -> Tuple[bool, Dict]:
    """Función de conveniencia para hacer una llamada."""
    try:
        client = get_pearl_client()
        return client.make_call(outbound_id, phone_number, lead_data)
    except Exception as e:
        logger.error(f"Error al hacer llamada: {e}")
        return False, {"error": str(e)}

if __name__ == "__main__":
    # Código de prueba
    print("🧪 Probando cliente Pearl AI...")
    
    try:
        client = get_pearl_client()
        print(f"✅ Cliente inicializado")
        
        # Probar conexión
        if client.test_connection():
            print("✅ Conexión exitosa")
            
            # Obtener campañas
            campaigns = client.get_outbound_campaigns()
            print(f"✅ Obtenidas {len(campaigns)} campañas")
            
            for campaign in campaigns[:3]:  # Mostrar solo las primeras 3
                print(f"   📋 Campaña: {campaign.get('id', 'N/A')} - {campaign.get('name', 'Sin nombre')}")
                
        else:
            print("❌ Error de conexión")
            
    except Exception as e:
        print(f"❌ Error: {e}")

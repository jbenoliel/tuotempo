#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para iniciar llamadas salientes a través de la API de NLPearl.

Este script se encarga de:
1. Cargar las credenciales de la API de NLPearl.
2. Obtener el ID de la campaña de llamadas (outbound) específica.
3. Leer los leads de la base de datos que están pendientes de ser llamados.
4. Iniciar la llamada para cada lead a través de la API 'make-call'.
"""

import os
import requests
import logging
from dotenv import load_dotenv
from db import get_connection
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_api_credentials():
    """Cargar credenciales de la API de Pearl desde variables de entorno."""
    # Cargar el archivo .env desde la ruta específica del proyecto PearlInfo
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'PearlInfo', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Cargando credenciales desde: {os.path.abspath(dotenv_path)}")
    account_id = os.getenv('PEARL_ACCOUNT_ID')
    secret_key = os.getenv('PEARL_SECRET_KEY')
    
    if not account_id or not secret_key:
        logger.error("ERROR: No se encontraron las credenciales de la API de Pearl en el archivo .env")
        logger.error("Asegúrate de que el archivo .env contiene PEARL_ACCOUNT_ID y PEARL_SECRET_KEY")
        return None, None
    
    logger.info("Credenciales de la API de Pearl cargadas correctamente.")
    return account_id, secret_key

def get_outbound_id(account_id, secret_key, outbound_name):
    """Obtener el ID de una campaña de llamadas salientes (outbound) por su nombre."""
    if not account_id or not secret_key:
        return None
    
    url = "https://api.nlpearl.ai/v1/Outbound"
    headers = {
        "Authorization": f"Bearer {account_id}:{secret_key}"
    }
    
    logger.info(f"Buscando el ID para la campaña de outbound: '{outbound_name}'")
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            outbounds = response.json()
            for outbound in outbounds:
                if outbound.get('name') == outbound_name:
                    outbound_id = outbound.get('id')
                    logger.info(f"ID de la campaña '{outbound_name}' encontrado: {outbound_id}")
                    return outbound_id
            
            logger.error(f"No se encontró ninguna campaña de outbound con el nombre: '{outbound_name}'")
            return None
        else:
            logger.error(f"Error al obtener las campañas de outbound. Código: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Excepción al obtener el ID de la campaña de outbound: {str(e)}")
        return None

def make_call(account_id, secret_key, outbound_id, lead_info):
    """Prepara y realiza una llamada saliente a un lead específico."""
    logger.info(f"Iniciando preparación de llamada para el lead con teléfono: {lead_info.get('telefono')}")

    # Lógica para el saludo dinámico
    saludo = "Buenos dias" if datetime.now().hour < 14 else "Buenas tardes"

    # Construir el payload del JSON con los datos del lead
    payload = {
        "phoneNumber": lead_info.get('telefono'),
        "firstName": lead_info.get('nombre'),
        "lastName": lead_info.get('apellidos'),
        "nif": lead_info.get('nif'),
        "fechaNacimiento": lead_info.get('fecha_nacimiento').strftime('%Y-%m-%d') if lead_info.get('fecha_nacimiento') else None,
        "sexo": lead_info.get('sexo'),
        "codigoPostal": lead_info.get('codigo_postal'),
        "certificado": lead_info.get('certificado'),
        "clinicaId": lead_info.get('clinica_id'),
        "nombreClinica": lead_info.get('nombre_clinica'),
        "direccionClinica": lead_info.get('direccion_clinica'),
        "delegacion": lead_info.get('delegacion'),
        "poliza": lead_info.get('poliza'),
        "segmento": lead_info.get('segmento'),
        "orden": lead_info.get('id_externo'), # Mapeado desde id_externo
        "dias_tardes": saludo
    }

    # Eliminar claves con valores nulos para no enviarlas
    payload = {k: v for k, v in payload.items() if v is not None}

    url = f"https://api.nlpearl.ai/v1/Outbound/{outbound_id}/make-call"
    headers = {
        "Authorization": f"Bearer {account_id}:{secret_key}",
        "Content-Type": "application/json"
    }

    logger.info(f"Enviando payload a NLPearl: {payload}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info(f"Llamada iniciada con éxito para el teléfono {lead_info.get('telefono')}. Respuesta: {response.json()}")
            return True
        else:
            logger.error(f"Error al iniciar la llamada para {lead_info.get('telefono')}. Código: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al realizar la llamada: {str(e)}")
        return False

def main():
    """Función principal para lanzar la campaña de llamadas."""
    logger.info("Iniciando el script para lanzar llamadas salientes...")
    
    account_id, secret_key = load_api_credentials()
    if not account_id or not secret_key:
        return

    outbound_name = "Outbound - Segurcaixa III- POC Tuotempo"
    outbound_id = get_outbound_id(account_id, secret_key, outbound_name)
    
    if not outbound_id:
        logger.error("No se pudo continuar sin el ID de la campaña de outbound.")
        return

    conn = get_connection()
    if not conn:
        logger.error("No se pudo obtener conexión a la base de datos. Abortando.")
        return

    try:
        with conn.cursor(dictionary=True) as cursor:
            # Seleccionar leads que no tengan un estado final y no tengan una rellamada programada para el futuro
            # y que no tengan un error técnico marcado.
            query = """ 
                SELECT * FROM leads 
                WHERE (status_level_1 IS NULL OR status_level_1 NOT IN ('No Interesado', 'Cita Agendada', 'Error'))
                AND (hora_rellamada IS NULL OR hora_rellamada <= NOW())
                AND (error_tecnico IS NULL OR error_tecnico = FALSE)
                LIMIT 10
            """
            cursor.execute(query)
            leads_to_call = cursor.fetchall()
            logger.info(f"Se encontraron {len(leads_to_call)} leads para llamar.")

            for lead in leads_to_call:
                make_call(account_id, secret_key, outbound_id, lead)
    
    except Exception as e:
        logger.error(f"Ocurrió un error al procesar los leads: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("Conexión a la base de datos cerrada.")

    logger.info("Proceso de lanzamiento de llamadas finalizado.")


if __name__ == "__main__":
    main()

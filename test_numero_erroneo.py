#!/usr/bin/env python3
"""
Script para probar el tratamiento de números erróneos
"""

import os
import sys
from config import settings
import pymysql
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_pymysql_connection():
    """Obtiene conexión PyMySQL con configuración de Railway"""
    try:
        return pymysql.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            port=settings.DB_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
    except Exception as e:
        logger.error(f"Error conectando a la BD: {e}")
        return None

def test_numero_erroneo():
    """
    Simula el flujo de tratamiento de número erróneo
    """
    # Simular datos de llamada con número erróneo
    test_data = [
        {
            'name': 'Pearl AI Status Code 6 (número inválido)',
            'call_result': {'success': False, 'status': 'failed', 'error_message': 'Invalid phone number'},
            'pearl_response': {'status': 6, 'conversationStatus': 'failed'}
        },
        {
            'name': 'Mensaje de error con "invalid number"',
            'call_result': {'success': False, 'status': 'error', 'error_message': 'invalid number'},
            'pearl_response': None
        },
        {
            'name': 'Mensaje de error con "number not in service"',
            'call_result': {'success': False, 'status': 'failed', 'error_message': 'number not in service'},
            'pearl_response': None
        },
        {
            'name': 'Error genérico que se clasifica como teléfono erróneo',
            'call_result': {'success': False, 'status': 'error', 'error_message': 'generic error'},
            'pearl_response': None
        }
    ]

    print("=== SIMULACIÓN DE TRATAMIENTO DE NÚMEROS ERRÓNEOS ===\n")

    for test in test_data:
        print(f"CASO: {test['name']}")
        print(f"Call Result: {test['call_result']}")
        print(f"Pearl Response: {test['pearl_response']}")

        # Simular determine_call_outcome
        outcome = simulate_determine_call_outcome(test['call_result'], test['pearl_response'])
        print(f"=> Outcome determinado: {outcome}")

        # Simular analyze_call_failure_type
        failure_type = simulate_analyze_call_failure_type(test['call_result'], test['pearl_response'])
        print(f"=> Failure type: {failure_type}")

        # Determinar acción
        action = determine_action(outcome, failure_type)
        print(f"=> Accion: {action}")
        print()

def simulate_determine_call_outcome(call_result, pearl_response):
    """Simula la función determine_call_outcome"""
    if call_result.get('success', False):
        return 'success'

    status = str(call_result.get('status', '')).lower()
    error_message = str(call_result.get('error_message') or '').lower()

    # Análisis del error message
    if 'busy' in error_message or 'ocupado' in error_message:
        return 'busy'
    elif ('invalid' in error_message or 'wrong number' in error_message or
          'not a valid' in error_message or 'unreachable' in error_message or
          'number not found' in error_message or 'not in service' in error_message):
        return 'invalid_phone'
    elif 'no answer' in error_message or 'sin respuesta' in error_message:
        return 'no_answer'
    elif 'hang up' in error_message or 'disconnect' in error_message:
        return 'hang_up'

    # Mapear por status
    status_mapping = {
        'busy': 'busy',
        'no_answer': 'no_answer',
        'failed': 'error',
        'error': 'error',
        'timeout': 'no_answer',
        'rejected': 'hang_up'
    }

    return status_mapping.get(status, 'error')

def simulate_analyze_call_failure_type(call_result, pearl_response):
    """Simula la función analyze_call_failure_type"""
    # Indicadores de número no válido
    invalid_phone_indicators = [
        'invalid number', 'numero invalido', 'numero inexistente',
        'number not in service', 'fuera de servicio', 'no existe',
        'invalid phone', 'telefono incorrecto', 'wrong number'
    ]

    # Análisis de Pearl AI status codes
    if pearl_response:
        status_code = pearl_response.get('status')
        if status_code == 6:  # Número no válido
            return 'invalid_phone'
        elif status_code == 7:  # No contesta
            return 'no_answer'
        elif status_code == 5:  # Busy
            return 'busy'

    # Análisis de texto
    analysis_text = ""
    if call_result:
        analysis_text += str(call_result).lower()
    if pearl_response:
        analysis_text += str(pearl_response).lower()

    if any(indicator in analysis_text for indicator in invalid_phone_indicators):
        return 'invalid_phone'
    else:
        return 'other'

def determine_action(outcome, failure_type):
    """Determina qué acción se tomaría según el outcome y failure_type"""
    if outcome == 'invalid_phone':
        return "CERRAR INMEDIATAMENTE - Teléfono erróneo (close_lead_immediately)"
    elif failure_type == 'invalid_phone':
        return "CERRAR INMEDIATAMENTE - Número no válido (close_lead_with_reason)"
    elif outcome in ['no_answer', 'busy', 'hang_up']:
        return "REPROGRAMAR - Reintentar más tarde"
    elif outcome == 'error':
        return "CERRAR INMEDIATAMENTE - Error genérico como teléfono erróneo"
    else:
        return "CERRAR INMEDIATAMENTE - Outcome no reconocido"

def verificar_leads_cerrados_por_telefono():
    """Verifica cuántos leads se han cerrado por teléfono erróneo"""
    conn = get_pymysql_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE lead_status = 'closed'
                AND (closure_reason LIKE '%tel%' OR closure_reason LIKE '%phone%' OR closure_reason LIKE '%err%')
            """)
            closed_count = cursor.fetchone()['count']

            cursor.execute("""
                SELECT closure_reason, COUNT(*) as count
                FROM leads
                WHERE lead_status = 'closed'
                AND (closure_reason LIKE '%tel%' OR closure_reason LIKE '%phone%' OR closure_reason LIKE '%err%')
                GROUP BY closure_reason
                ORDER BY count DESC
            """)
            closure_reasons = cursor.fetchall()

            print("=== ESTADÍSTICAS DE LEADS CERRADOS ===")
            print(f"Total leads cerrados por teléfono/error: {closed_count}")
            print("\nRazones de cierre:")
            for reason in closure_reasons:
                print(f"  - {reason['closure_reason']}: {reason['count']} leads")

    except Exception as e:
        logger.error(f"Error verificando leads cerrados: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== TEST DE NÚMEROS ERRÓNEOS ===\n")
    test_numero_erroneo()
    print("\n")
    verificar_leads_cerrados_por_telefono()
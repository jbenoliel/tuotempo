"""
Integración del Scheduler con el Call Manager existente.
Este módulo extiende el call_manager.py para usar automáticamente el scheduler.
"""

import logging
from datetime import datetime
from typing import Dict, Optional
from call_scheduler import schedule_failed_call
from db import get_connection

logger = logging.getLogger(__name__)

def enhanced_process_call_result(lead_id: int, call_result: Dict, pearl_response: Dict = None):
    """
    Procesa el resultado de una llamada e integra con el scheduler automáticamente.
    
    Args:
        lead_id: ID del lead
        call_result: Resultado de la llamada de Pearl AI
        pearl_response: Respuesta completa de la API de Pearl
    """
    try:
        # Extraer información del resultado
        raw_status = call_result.get('status', 'failed')
        mapped_status = map_status_to_db_enum(raw_status)
        success = call_result.get('success', False)
        duration = call_result.get('duration', 0)
        error_message = call_result.get('error_message')
        
        # Determinar el outcome para el scheduler
        outcome = determine_call_outcome(call_result, pearl_response)
        
        # Actualizar el lead en la BD
        update_lead_with_call_result(lead_id, mapped_status, outcome, error_message, pearl_response)
        
        # Manejar casos según el tipo de error
        if not success:
            if outcome == 'invalid_phone':
                # Teléfonos inválidos se cierran inmediatamente SIN reprogramar
                logger.info(f"Teléfono inválido para lead {lead_id}. Cerrando directamente.")
                close_lead_immediately(lead_id, outcome, 'Teléfono erróneo')
                
            elif outcome in ['no_answer', 'busy', 'hang_up']:
                # Estos casos se reprograman
                logger.info(f"Llamada fallida para lead {lead_id} ({outcome}). Usando scheduler para reprogramar.")
                
                # Intentar reprogramar con el scheduler
                scheduled = schedule_failed_call(lead_id, outcome)
                
                if scheduled:
                    logger.info(f"Lead {lead_id} reprogramado exitosamente por el scheduler")
                else:
                    logger.info(f"Lead {lead_id} cerrado por el scheduler (máximo intentos alcanzado)")
                    
            elif outcome == 'error':
                # Errores genéricos también se cierran (podrían ser números incorrectos)
                logger.info(f"Error genérico para lead {lead_id}. Cerrando como teléfono erróneo.")
                close_lead_immediately(lead_id, 'invalid_phone', 'Teléfono erróneo')
                
            else:
                # Cualquier otro outcome no reconocido - cerrar por seguridad
                logger.warning(f"Outcome no reconocido '{outcome}' para lead {lead_id}. Cerrando.")
                close_lead_immediately(lead_id, 'invalid_phone', 'Teléfono erróneo')
        
        elif success:
            # Llamada exitosa - marcar como completada y cerrar el lead si hay cita
            mark_successful_call(lead_id, call_result)
            logger.info(f"Llamada exitosa para lead {lead_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error procesando resultado de llamada para lead {lead_id}: {e}")
        return False

def map_status_to_db_enum(status: str) -> str:
    """
    Mapea el status de Pearl AI a los valores válidos del ENUM de call_status.
    
    Args:
        status: Status de Pearl AI
        
    Returns:
        str: Valor válido para el ENUM call_status
    """
    status_lower = str(status).lower()
    
    # Mapeo de status de Pearl AI a ENUM de BD
    status_mapping = {
        'completed': 'completed',
        'success': 'completed',
        'busy': 'busy',
        'no_answer': 'no_answer',
        'failed': 'error',
        'error': 'error',
        'timeout': 'no_answer',
        'rejected': 'error',
        'calling': 'calling',
        'selected': 'selected',
        'in_progress': 'calling'
    }
    
    return status_mapping.get(status_lower, 'error')

def determine_call_outcome(call_result: Dict, pearl_response: Dict = None) -> str:
    """
    Determina el outcome de la llamada para el scheduler.
    
    Returns:
        str: 'no_answer', 'busy', 'hang_up', 'error', 'success', 'invalid_phone'
    """
    if call_result.get('success', False):
        return 'success'
    
    # Mapear status de Pearl AI a outcomes del scheduler
    status = call_result.get('status', '').lower()
    error_message = call_result.get('error_message', '').lower()
    
    # Análisis del error message si está disponible - PRIORIDAD en este orden
    # 1. BUSY/OCUPADO - Reprogramar
    if 'busy' in error_message or 'ocupado' in error_message or 'line busy' in error_message:
        return 'busy'
    
    # 2. ERRORES DE TELÉFONO - Cerrar como número incorrecto
    elif ('invalid' in error_message or 'inválido' in error_message or 
          'wrong number' in error_message or 'número incorrecto' in error_message or
          'not a valid' in error_message or 'no válido' in error_message or
          'unreachable' in error_message or 'inalcanzable' in error_message or
          'number not found' in error_message or 'número no encontrado' in error_message or
          'failed to connect' in error_message or 'connection failed' in error_message or
          'network error' in error_message or 'error de red' in error_message):
        return 'invalid_phone'
    
    # 3. NO ANSWER - Reprogramar  
    elif 'no answer' in error_message or 'no contest' in error_message or 'sin respuesta' in error_message:
        return 'no_answer'
        
    # 4. HANG UP - Reprogramar (puede que contesten la próxima vez)
    elif 'hang up' in error_message or 'colg' in error_message or 'disconnect' in error_message:
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

def update_lead_with_call_result(lead_id: int, status: str, outcome: str, 
                                error_message: Optional[str], pearl_response: Dict = None):
    """
    Actualiza el lead con el resultado de la llamada.
    """
    conn = get_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Actualizar lead con resultado de la llamada
            sql = """
                UPDATE leads SET
                    call_status = %s,
                    call_attempts_count = IFNULL(call_attempts_count,0) + 1,
                    last_call_attempt = NOW(),
                    call_error_message = %s,
                    pearl_call_response = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            pearl_response_json = None
            if pearl_response:
                import json
                pearl_response_json = json.dumps(pearl_response)
            
            cursor.execute(sql, (status, error_message, pearl_response_json, lead_id))
            
            # Si es una llamada exitosa y hay confirmación de cita, actualizar status_level_1
            if outcome == 'success':
                # Aquí podrías añadir lógica para determinar si se agendó una cita
                # basándose en la respuesta de Pearl AI
                pass
            
            conn.commit()
            
            logger.info(f"Lead {lead_id} actualizado: status={status}, outcome={outcome}")
            return True
            
    except Exception as e:
        logger.error(f"Error actualizando lead {lead_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        conn.close()

def mark_successful_call(lead_id: int, call_result: Dict):
    """
    Marca una llamada como exitosa y potencialmente cierra el lead.
    """
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Si la llamada fue exitosa, podríamos querer cerrar el lead
            # dependiendo de si se agendó una cita o hubo rechazo definitivo
            
            # Por ahora, solo marcamos como completada
            cursor.execute("""
                UPDATE leads SET
                    call_status = 'completed',
                    last_call_attempt = NOW(),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (lead_id,))
            
            conn.commit()
            logger.info(f"Lead {lead_id} marcado como llamada exitosa")
            
    except Exception as e:
        logger.error(f"Error marcando llamada exitosa para lead {lead_id}: {e}")
    finally:
        conn.close()

def get_leads_from_scheduler(limit: int = 10) -> list:
    """
    Obtiene leads que están programados por el scheduler para llamar ahora.
    """
    from call_scheduler import get_next_scheduled_calls
    return get_next_scheduled_calls(limit)

def integrate_scheduler_with_call_manager():
    """
    Función para integrar el scheduler con el call manager existente.
    
    Esta función puede ser llamada desde el call_manager para usar
    automáticamente las llamadas programadas por el scheduler.
    """
    try:
        # Obtener llamadas pendientes del scheduler
        scheduled_calls = get_leads_from_scheduler(50)
        
        if not scheduled_calls:
            logger.info("No hay llamadas programadas pendientes")
            return []
        
        logger.info(f"Encontradas {len(scheduled_calls)} llamadas programadas")
        
        # Convertir a formato esperado por el call_manager
        leads_for_calling = []
        for call in scheduled_calls:
            lead_data = {
                'id': call['lead_id'],
                'nombre': call['nombre'],
                'apellidos': call['apellidos'],
                'telefono': call['telefono'],
                'schedule_id': call['schedule_id'],
                'attempt_number': call['attempt_number']
            }
            leads_for_calling.append(lead_data)
        
        return leads_for_calling
        
    except Exception as e:
        logger.error(f"Error integrando scheduler con call manager: {e}")
        return []

# Función de callback para usar en el call_manager
def on_call_completed_callback(lead_id: int, phone: str, result: Dict):
    """Callback para cuando se completa una llamada."""
    enhanced_process_call_result(lead_id, result)

def on_call_failed_callback(lead_id: int, phone: str, result: Dict):
    """Callback para cuando falla una llamada."""
    enhanced_process_call_result(lead_id, result)

# Funciones de utilidad para monitoreo
def get_scheduler_integration_stats():
    """Obtiene estadísticas de la integración scheduler-call_manager."""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        with conn.cursor(dictionary=True) as cursor:
            stats = {}
            
            # Llamadas programadas hoy
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM call_schedule 
                WHERE DATE(scheduled_at) = CURDATE() AND status = 'pending'
            """)
            stats['scheduled_today'] = cursor.fetchone()['count']
            
            # Llamadas que deberían ejecutarse ahora
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending' 
                    AND cs.scheduled_at <= NOW()
                    AND l.lead_status = 'open'
            """)
            stats['due_now'] = cursor.fetchone()['count']
            
            # Leads cerrados por el scheduler en las últimas 24h
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM leads 
                WHERE lead_status = 'closed' 
                    AND closure_reason IS NOT NULL
                    AND updated_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            stats['closed_last_24h'] = cursor.fetchone()['count']
            
            return stats
            
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de integración: {e}")
        return {}
    finally:
        conn.close()

def close_lead_immediately(lead_id: int, outcome: str, closure_reason: str):
    """
    Cierra un lead inmediatamente sin reprogramar.
    Se usa para teléfonos inválidos o errores que no deben reintentarse.
    """
    conn = get_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD para cerrar lead")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Cerrar el lead
            cursor.execute("""
                UPDATE leads 
                SET lead_status = 'closed',
                    closure_reason = %s,
                    call_status = %s,
                    updated_at = NOW(),
                    selected_for_calling = FALSE
                WHERE id = %s
            """, (closure_reason, str(outcome)[:50], lead_id))
            
            # Cancelar cualquier llamada programada pendiente
            cursor.execute("""
                UPDATE call_schedule 
                SET status = 'cancelled', 
                    updated_at = NOW()
                WHERE lead_id = %s AND status = 'pending'
            """, (lead_id,))
            
            conn.commit()
            
            affected_rows = cursor.rowcount
            if affected_rows > 0:
                logger.info(f"✅ Lead {lead_id} cerrado inmediatamente: {closure_reason}")
                return True
            else:
                logger.warning(f"⚠️  No se pudo cerrar lead {lead_id} (no existe o ya cerrado)")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error cerrando lead {lead_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # Prueba de la integración
    print("Probando integración scheduler-call_manager...")
    
    # Obtener estadísticas
    stats = get_scheduler_integration_stats()
    print(f"Estadísticas: {stats}")
    
    # Obtener llamadas programadas
    scheduled = integrate_scheduler_with_call_manager()
    print(f"Llamadas programadas: {len(scheduled)}")
    
    for call in scheduled:
        print(f"  - Lead {call['id']}: {call['nombre']} {call['apellidos']} (intento {call['attempt_number']})")
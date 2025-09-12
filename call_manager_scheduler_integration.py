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
    # Safety checks at the very beginning
    if lead_id is None or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id: {lead_id}")
        return False
    if call_result is None:
        logger.error(f"call_result is None for lead {lead_id}")
        return False
        
    try:
        # Extraer información del resultado
        raw_status = call_result.get('status', 'failed')
        mapped_status = map_status_to_db_enum(raw_status)
        success = call_result.get('success', False)
        duration = call_result.get('duration', 0)
        error_message = call_result.get('error_message') or ''
        
        # Determinar el outcome para el scheduler
        outcome = determine_call_outcome(call_result, pearl_response)
        
        # Actualizar el lead en la BD
        # Additional safety checks with logging
        if mapped_status is None:
            logger.error(f"mapped_status is None for lead {lead_id}, using default 'failed'")
            mapped_status = 'failed'
        if outcome is None:
            logger.error(f"outcome is None for lead {lead_id}, using default 'error'")
            outcome = 'error'
        
        try:
            update_lead_with_call_result(lead_id, mapped_status, outcome, error_message, pearl_response)
        except Exception as e:
            logger.error(f"Critical error in update_lead_with_call_result for lead {lead_id}: {e}")
            # Return early to avoid further processing that could cause none_dealloc
            return False
        
        # Manejar casos según el tipo de error - wrapped in try-catch
        try:
            if not success:
                if outcome == 'invalid_phone':
                    # Teléfonos inválidos se cierran inmediatamente SIN reprogramar
                    logger.info(f"Teléfono inválido para lead {lead_id}. Cerrando directamente.")
                    try:
                        close_lead_immediately(lead_id, outcome, 'Teléfono erróneo')
                    except Exception as e:
                        logger.error(f"Error closing lead {lead_id}: {e}")
                    
                elif outcome in ['no_answer', 'busy', 'hang_up']:
                    # Estos casos se reprograman
                    logger.info(f"Llamada fallida para lead {lead_id} ({outcome}). Usando scheduler para reprogramar.")
                    
                    # Intentar reprogramar con el scheduler
                    try:
                        scheduled = schedule_failed_call(lead_id, outcome)
                        
                        if scheduled:
                            logger.info(f"Lead {lead_id} reprogramado exitosamente por el scheduler")
                        else:
                            logger.info(f"Lead {lead_id} cerrado por el scheduler (máximo intentos alcanzado)")
                    except Exception as e:
                        logger.error(f"Error scheduling failed call for lead {lead_id}: {e}")
                        
                elif outcome == 'error':
                    # Errores genéricos también se cierran (podrían ser números incorrectos)
                    logger.info(f"Error genérico para lead {lead_id}. Cerrando como teléfono erróneo.")
                    try:
                        close_lead_immediately(lead_id, 'invalid_phone', 'Teléfono erróneo')
                    except Exception as e:
                        logger.error(f"Error closing lead {lead_id}: {e}")
                    
                else:
                    # Cualquier otro outcome no reconocido - cerrar por seguridad
                    logger.warning(f"Outcome no reconocido '{outcome}' para lead {lead_id}. Cerrando.")
                    try:
                        close_lead_immediately(lead_id, 'invalid_phone', 'Teléfono erróneo')
                    except Exception as e:
                        logger.error(f"Error closing lead {lead_id}: {e}")
            
            elif success:
                # Llamada exitosa - marcar como completada y cerrar el lead si hay cita
                try:
                    mark_successful_call(lead_id, call_result, pearl_response)
                    logger.info(f"Llamada exitosa para lead {lead_id}")
                except Exception as e:
                    logger.error(f"Error marking successful call for lead {lead_id}: {e}")
        except Exception as e:
            logger.error(f"Critical error in call outcome handling for lead {lead_id}: {e}")
            return False
        
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
    status = str(call_result.get('status', '')).lower()
    error_message = str(call_result.get('error_message') or '').lower()
    
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
    # Comprehensive safety checks
    if lead_id is None or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id: {lead_id}")
        return False
    if status is None:
        logger.error(f"status is None for lead {lead_id}, using 'error'")
        status = 'error'
    if outcome is None:
        logger.error(f"outcome is None for lead {lead_id}, using 'error'")
        outcome = 'error'
    if error_message is None:
        error_message = ''
        
    conn = get_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return False
    
    try:
        with conn.cursor() as cursor:
            # Ensure all parameters are strings and not None
            safe_status = str(status) if status is not None else 'error'
            safe_error_message = str(error_message) if error_message is not None else ''
            safe_lead_id = int(lead_id) if lead_id is not None else 0
            
            if safe_lead_id == 0:
                logger.error("Invalid lead_id, cannot update database")
                return False
            
            # Actualizar lead con resultado de la llamada - simplified query
            sql = """
                UPDATE leads SET
                    call_status = %s,
                    call_attempts_count = IFNULL(call_attempts_count,0) + 1,
                    last_call_attempt = NOW(),
                    call_error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            
            cursor.execute(sql, (safe_status, safe_error_message, safe_lead_id))
            
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

def mark_successful_call(lead_id: int, call_result: Dict, pearl_response: Dict = None):
    """
    Marca una llamada como exitosa y procesa la información de cita si está disponible.
    """
    # Safety check for lead_id
    if lead_id is None or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id: {lead_id}")
        return False
        
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Valores por defecto usando el mapeo correcto
            # Determinar el status correcto basado en call_result
            raw_status = call_result.get('status', 'success') if call_result.get('success', False) else 'failed'
            mapped_status = map_status_to_db_enum(raw_status)
            
            update_fields = {
                'call_status': mapped_status,  # Usar status mapeado correctamente
                'last_call_attempt': 'NOW()',
                'updated_at': 'CURRENT_TIMESTAMP'
            }
            
            # Procesar información de cita si está disponible
            if pearl_response and 'collectedInfo' in pearl_response:
                collected_info = pearl_response['collectedInfo']
                logger.info(f"Procesando collectedInfo para lead {lead_id}: {collected_info}")
                
                # Extraer información de cita
                fecha_deseada = None
                hora_deseada = None
                call_result_info = None
                preferencia_mt = None
                
                # Buscar en la lista de collected_info
                for item in collected_info:
                    if item.get('id') == 'fechaDeseada':
                        fecha_deseada = item.get('value')
                    elif item.get('id') == 'horaDeseada':
                        hora_deseada = item.get('value')
                    elif item.get('id') == 'callResult':
                        call_result_info = item.get('value')
                    elif item.get('id') == 'preferenciaMT':
                        preferencia_mt = item.get('value')
                
                logger.info(f"Lead {lead_id} - Datos extraídos: fecha={fecha_deseada}, hora={hora_deseada}, resultado={call_result_info}, preferencia={preferencia_mt}")
                
                # Determinar si hay cita basándose ÚNICAMENTE en la presencia de fechaDeseada
                tiene_cita = bool(fecha_deseada)
                logger.info(f"Lead {lead_id} - Tiene cita: {tiene_cita}")
                
                # Procesar fecha de cita si está disponible
                if fecha_deseada:
                    try:
                        # Convertir formato DD-MM-YYYY a YYYY-MM-DD para MySQL
                        if '-' in fecha_deseada and len(fecha_deseada.split('-')) == 3:
                            parts = fecha_deseada.split('-')
                            if len(parts[0]) == 2:  # DD-MM-YYYY
                                mysql_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                                update_fields['cita'] = mysql_date  # Sin comillas
                                logger.info(f"Lead {lead_id} - Fecha de cita procesada: {mysql_date}")
                    except Exception as e:
                        logger.warning(f"Error procesando fecha {fecha_deseada} para lead {lead_id}: {e}")
                
                # Procesar hora de cita si está disponible (OPCIONAL)
                if hora_deseada:
                    try:
                        # Asegurar formato HH:MM:SS
                        if ':' in hora_deseada:
                            time_parts = hora_deseada.split(':')
                            if len(time_parts) >= 2:
                                # Asegurar formato completo HH:MM:SS
                                if len(time_parts) == 2:
                                    hora_deseada += ':00'
                                update_fields['hora_cita'] = hora_deseada  # Sin comillas
                                logger.info(f"Lead {lead_id} - Hora de cita procesada: {hora_deseada}")
                    except Exception as e:
                        logger.warning(f"Error procesando hora {hora_deseada} para lead {lead_id}: {e}")
                
                # Actualizar status ÚNICAMENTE basado en la presencia de fechaDeseada
                if tiene_cita:
                    update_fields['status_level_1'] = "Cita Agendada"  # Sin comillas
                    # Opcional: actualizar resultado_llamada solo si hay un resultado específico
                    if call_result_info and 'cita reservada' in call_result_info.lower():
                        update_fields['resultado_llamada'] = "Cita confirmada"  # Sin comillas
                    
                    # CERRAR EL LEAD cuando hay cita (igual que con "No Interesado")
                    update_fields['lead_status'] = "closed"  # Sin comillas
                    update_fields['closure_reason'] = "Cita agendada"  # Sin comillas
                    update_fields['selected_for_calling'] = 'FALSE'
                    
                    logger.info(f"Lead {lead_id} - Estado actualizado a 'Cita Agendada' y CERRADO por presencia de fechaDeseada")
                else:
                    logger.info(f"Lead {lead_id} - Sin información de cita (fechaDeseada faltante)")
                
            # Construir query de actualización con parámetros seguros
            set_clauses = []
            query_params = []
            
            for field, value in update_fields.items():
                # Convertir valor a string para comparaciones
                value_str = str(value)
                
                if value_str in ['NOW()', 'CURRENT_TIMESTAMP']:
                    # Funciones especiales que no necesitan parámetros
                    set_clauses.append(f"{field} = {value_str}")
                    logger.info(f"Lead {lead_id} - Campo {field}: función especial {value_str}")
                elif value_str == 'FALSE' or value is False:
                    # Booleano FALSE
                    set_clauses.append(f"{field} = FALSE")
                    logger.info(f"Lead {lead_id} - Campo {field}: booleano FALSE")
                else:
                    # Valores regulares con parámetros seguros
                    set_clauses.append(f"{field} = %s")
                    # Limpiar cualquier comilla que pueda tener el valor
                    clean_value = value_str.strip("'\"") if isinstance(value, str) else value
                    query_params.append(clean_value)
                    logger.info(f"Lead {lead_id} - Campo {field}: valor='{clean_value}', tipo={type(clean_value)}")
            
            # Agregar el lead_id al final
            query_params.append(lead_id)
            
            sql = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = %s"
            
            # Debug logging para identificar el problema
            logger.info(f"Lead {lead_id} - SQL generado: {sql}")
            logger.info(f"Lead {lead_id} - Parámetros: {tuple(query_params)}")
            logger.info(f"Lead {lead_id} - Update fields: {update_fields}")
            
            cursor.execute(sql, tuple(query_params))
            
            conn.commit()
            
            if update_fields.get('cita') or update_fields.get('status_level_1'):
                logger.info(f"✅ Lead {lead_id} procesado exitosamente con información de cita")
            else:
                logger.info(f"✅ Lead {lead_id} marcado como llamada exitosa (sin información de cita)")
            
    except Exception as e:
        logger.error(f"Error marcando llamada exitosa para lead {lead_id}: {e}")
        if conn:
            conn.rollback()
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
    # Safety checks
    if lead_id is None or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id: {lead_id}")
        return False
    if outcome is None:
        outcome = 'unknown'
    if closure_reason is None:
        closure_reason = 'Error desconocido'
    
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
"""
Integración del Scheduler con el Call Manager existente.
Este módulo extiende el call_manager.py para usar automáticamente el scheduler.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Optional
from reprogramar_llamadas_simple import simple_reschedule_failed_call, get_pymysql_connection, cancel_scheduled_calls_for_lead
from db import get_connection

logger = logging.getLogger(__name__)

def check_and_close_if_not_interested(lead_id: int, call_result: Dict, pearl_response: Dict = None, telefono: str = None) -> bool:
    """
    Verifica si el resultado indica 'No Interesado' y cierra el lead inmediatamente.
    
    Args:
        lead_id: ID del lead
        call_result: Resultado de la llamada
        pearl_response: Respuesta de Pearl AI
        
    Returns:
        bool: True si se cerró el lead por 'No Interesado'
    """
    if not lead_id or not isinstance(lead_id, int):
        return False
    
    # Buscar indicadores de "No Interesado" en los datos
    not_interested_indicators = [
        'no interesado', 'not interested', 'no interesa', 
        'no le interesa', 'desinteresado', 'rechaza'
    ]
    
    # Verificar en call_result
    if call_result:
        call_result_str = str(call_result).lower()
        if any(indicator in call_result_str for indicator in not_interested_indicators):
            close_lead_with_reason(lead_id, 'No interesado', telefono)
            return True
    
    # Verificar en pearl_response si está disponible
    if pearl_response and isinstance(pearl_response, dict):
        # Verificar en collectedInfo
        collected_info = pearl_response.get('collectedInfo')
        if collected_info:
            collected_str = str(collected_info).lower()
            if any(indicator in collected_str for indicator in not_interested_indicators):
                close_lead_with_reason(lead_id, 'No interesado', telefono)
                return True
    
    return False

def analyze_call_failure_type(call_result: Dict, pearl_response: Dict = None) -> str:
    """
    Analiza el tipo de fallo de llamada para determinar la razón exacta
    
    Args:
        call_result: Resultado de la llamada
        pearl_response: Respuesta de Pearl AI
        
    Returns:
        str: Tipo de fallo ('invalid_phone', 'no_answer', 'busy', 'other')
    """
    # Indicadores de número no válido
    invalid_phone_indicators = [
        'invalid number', 'numero invalido', 'numero inexistente',
        'number not in service', 'fuera de servicio', 'no existe',
        'invalid phone', 'telefono incorrecto', 'wrong number'
    ]
    
    # Indicadores de no contesta
    no_answer_indicators = [
        'no answer', 'no contesta', 'no responde', 'sin respuesta',
        'voicemail', 'buzon', 'answering machine'
    ]
    
    # Indicadores de ocupado
    busy_indicators = [
        'busy', 'ocupado', 'linea ocupada', 'line busy'
    ]
    
    # Convertir datos a string para análisis
    analysis_text = ""
    
    if call_result:
        analysis_text += str(call_result).lower()
    
    if pearl_response:
        # Analizar campos específicos de Pearl AI
        status_code = pearl_response.get('status')
        conversation_status = pearl_response.get('conversationStatus')
        
        # Pearl AI status codes específicos
        if status_code == 6:  # Número no válido en Pearl AI
            return 'invalid_phone'
        elif status_code == 7:  # No contesta
            return 'no_answer'
        elif status_code == 5:  # Busy
            return 'busy'
        
        analysis_text += str(pearl_response).lower()
    
    # Análisis por texto
    if any(indicator in analysis_text for indicator in invalid_phone_indicators):
        return 'invalid_phone'
    elif any(indicator in analysis_text for indicator in no_answer_indicators):
        return 'no_answer'  
    elif any(indicator in analysis_text for indicator in busy_indicators):
        return 'busy'
    else:
        return 'other'

def close_lead_with_reason(lead_id: int, reason: str, telefono: str = None) -> bool:
    """
    Cierra un lead con una razón específica
    
    Args:
        lead_id: ID del lead
        reason: Razón del cierre
        
    Returns:
        bool: True si se cerró exitosamente
    """
    conn = None
    try:
        conn = get_pymysql_connection()
        if not conn:
            logger.error(f"No se pudo conectar para cerrar lead {lead_id}")
            return False
            
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE leads
                SET lead_status = 'closed',
                    closure_reason = %s,
                    selected_for_calling = FALSE,
                    updated_at = NOW()
                WHERE id = %s AND lead_status = 'open'
            """, (reason, lead_id))
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Lead {lead_id} cerrado por: {reason}")
                return True
            # Fallback: si no encontró por id, intentar cerrar por teléfono
            if telefono:
                try:
                    phone_digits = re.sub(r'[^0-9]', '', telefono)
                    cursor.execute(
                        "SELECT id FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s",
                        (phone_digits,)
                    )
                    matches = cursor.fetchall()
                    logger.debug(f"[DEBUG_CLOSE] Leads coincidentes por teléfono {telefono}: {matches}")
                    if matches:
                        fallback_id = matches[0]['id']
                        cursor.execute(
                            """
                            UPDATE leads
                            SET lead_status = 'closed',
                                closure_reason = %s,
                                selected_for_calling = FALSE,
                                updated_at = NOW()
                            WHERE id = %s AND lead_status = 'open'
                            """,
                            (reason, fallback_id)
                        )
                        if cursor.rowcount != 0:
                            conn.commit()
                            logger.info(f"Lead {fallback_id} cerrado por teléfono fallback: {telefono}")
                            return True
                except Exception as fe:
                    logger.warning(f"Fallback close_lead_with_reason error: {fe}")
            # Verificar si el lead existe pero ya está cerrado
            cursor.execute("SELECT id, lead_status FROM leads WHERE id = %s", (lead_id,))
            lead_info = cursor.fetchone()
            if lead_info and lead_info['lead_status'] == 'closed':
                logger.info(f"Lead {lead_id} ya estaba cerrado, no requiere cierre")
            else:
                logger.warning(f"No se pudo cerrar lead {lead_id} - no encontrado")
            return False
                
    except Exception as e:
        logger.error(f"Error cerrando lead {lead_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
        
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def increment_call_attempts_count(lead_id: int, telefono: str = None) -> bool:
    """
    Incrementa el contador de intentos de llamada en +1
    Se ejecuta cada vez que se realiza un intento, independiente del resultado
    
    Args:
        lead_id: ID del lead
        
    Returns:
        bool: True si se incrementó exitosamente
    """
    if not lead_id or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id for increment_call_attempts_count: {lead_id}")
        return False
    
    conn = None
    try:
        conn = get_pymysql_connection()
        if not conn:
            logger.error(f"No se pudo conectar para incrementar contador de lead {lead_id}")
            return False
            
        with conn.cursor() as cursor:
            # Incrementar contador de intentos (tratar NULL como abierto)
            cursor.execute("""
                UPDATE leads l
                SET call_attempts_count = (
                        SELECT COUNT(*) FROM pearl_calls pc WHERE pc.lead_id = l.id
                    ),
                    last_call_attempt = NOW(),
                    updated_at = NOW()
                WHERE id = %s AND (lead_status IS NULL OR lead_status = 'open')
            """, (lead_id,))
            if cursor.rowcount != 0:
                conn.commit()
                # Obtener el nuevo valor para logging
                cursor.execute("SELECT call_attempts_count FROM leads WHERE id = %s", (lead_id,))
                result = cursor.fetchone()
                new_count = result['call_attempts_count'] if result else 0
                logger.info(f"Incrementado contador de llamadas para lead {lead_id}: {new_count}")
                return True
            else:
                # Puede ocurrir que no haya filas afectadas si los valores ya coinciden
                # Verificamos si el lead existe y está abierto/NULL para considerarlo éxito
                cursor.execute("SELECT id, lead_status FROM leads WHERE id = %s", (lead_id,))
                lead_info_check = cursor.fetchone()
                if lead_info_check and (lead_info_check['lead_status'] is None or lead_info_check['lead_status'] == 'open'):
                    logger.info(f"Lead {lead_id} ya tenía los valores actualizados (sin filas afectadas). Considerando incremento como OK")
                    return True
            # Fallback: intentar incrementar por teléfono si se proporcionó
            if telefono:
                try:
                    phone_digits = re.sub(r'[^0-9]', '', telefono)
                    # Intentar coincidir leads por teléfono si id falló
                    cursor.execute(
                        "SELECT id FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s",
                        (phone_digits,)
                    )
                    matches = cursor.fetchall()
                    logger.debug(f"[DEBUG_INCREMENT] Leads coincidentes por teléfono {telefono}: {matches}")
                    if matches:
                        fallback_id = matches[0]['id']
                        logger.info(f"[DEBUG_INCREMENT] Usando lead_id de fallback: {fallback_id} para incremento")
                        cursor.execute(
                            """
                            UPDATE leads l
                            SET call_attempts_count = (
                                    SELECT COUNT(*) FROM pearl_calls pc WHERE pc.lead_id = l.id
                                ),
                                last_call_attempt = NOW(),
                                updated_at = NOW()
                            WHERE id = %s AND (lead_status IS NULL OR lead_status = 'open')
                            """,
                            (fallback_id,)
                        )
                        if cursor.rowcount != 0:
                            conn.commit()
                            logger.info(f"Fallback: incrementado contador para lead {fallback_id} (tel={telefono})")
                            return True
                        else:
                            # Verificar existencia/estado para considerar OK
                            cursor.execute("SELECT id, lead_status FROM leads WHERE id = %s", (fallback_id,))
                            fb_info = cursor.fetchone()
                            if fb_info and (fb_info['lead_status'] is None or fb_info['lead_status'] == 'open'):
                                logger.info(f"Fallback: lead {fallback_id} ya estaba actualizado (sin filas afectadas). Considerando incremento como OK")
                                return True
                except Exception as fe:
                    logger.warning(f"Fallback increment_call_attempts_count error: {fe}")
            # Verificar si el lead existe pero está cerrado
            cursor.execute("SELECT id, lead_status FROM leads WHERE id = %s", (lead_id,))
            lead_info = cursor.fetchone()
            if lead_info and lead_info['lead_status'] == 'closed':
                logger.info(f"Lead {lead_id} ya está cerrado, no se actualiza contador")
            else:
                logger.warning(f"No se pudo incrementar contador para lead {lead_id} - lead no encontrado")
            return False
                
    except Exception as e:
        logger.error(f"Error incrementando contador para lead {lead_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
        
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def enhanced_process_call_result(lead_id: int, call_result: Dict, pearl_response: Dict = None, telefono: str = None):
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
    
    # REGLA DE NEGOCIO: Al realizar cualquier llamada (programada o no programada),
    # cancelar todas las llamadas programadas pendientes para ese lead
    cancelled_count = cancel_scheduled_calls_for_lead(lead_id, "Llamada realizada - cancelando programaciones pendientes")
    if cancelled_count > 0:
        logger.info(f"Canceladas {cancelled_count} llamadas programadas para lead {lead_id} antes de procesar resultado")
    
        # INCREMENTAR CONTADOR DE LLAMADAS: +1 por cada intento, con fallback por teléfono
    increment_call_attempts_count(lead_id, telefono)
    
    # VERIFICAR SI EL LEAD DICE "NO INTERESADO" Y CERRARLO INMEDIATAMENTE
    if check_and_close_if_not_interested(lead_id, call_result, pearl_response, telefono):
        logger.info(f"Lead {lead_id} cerrado automáticamente por 'No Interesado'")
        return True
        
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
                            close_lead_immediately(lead_id, outcome, 'Teléfono erróneo', telefono)
                        except Exception as e:
                            logger.error(f"Error closing lead {lead_id}: {e}")
                    
                elif outcome in ['no_answer', 'busy', 'hang_up']:
                    # Análisis detallado del tipo de fallo
                    failure_type = analyze_call_failure_type(call_result, pearl_response)
                    logger.info(f"Análisis detallado para lead {lead_id}: outcome={outcome}, failure_type={failure_type}")
                    
                    if failure_type == 'invalid_phone':
                        # Número no válido - cerrar inmediatamente
                        logger.info(f"Lead {lead_id} identificado como número no válido - cerrando")
                        try:
                            close_lead_with_reason(lead_id, 'Ilocalizable - Número no válido', telefono)
                        except Exception as e:
                            logger.error(f"Error cerrando lead {lead_id} por número no válido: {e}")
                    else:
                        # Casos que se pueden reprogramar (no contesta, busy, hang_up)
                        logger.info(f"Llamada fallida para lead {lead_id} ({outcome}). Reprogramando...")
                        
                        # Usar versión segura de reprogramación
                        try:
                            scheduled = simple_reschedule_failed_call(lead_id, outcome)
                            if scheduled:
                                logger.info(f"Lead {lead_id} reprogramado exitosamente")
                            else:
                                logger.info(f"Lead {lead_id} cerrado por máximo intentos alcanzado")
                        except Exception as e:
                            logger.error(f"Error en reprogramación para lead {lead_id}: {e}")
                        
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
                    mark_successful_call(lead_id, call_result, None)  # Revertir temporalmente
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
        
    conn = get_pymysql_connection()
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
                UPDATE leads l SET
                    call_status = %s,
                    call_attempts_count = (
                        SELECT COUNT(*) FROM pearl_calls pc WHERE pc.lead_id = l.id
                    ),
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
    
    # Safety check for call_result
    if call_result is None:
        logger.error(f"call_result is None for lead {lead_id}")
        return False
        
    conn = get_pymysql_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Valores por defecto usando el mapeo correcto
            # Determinar el status correcto basado en call_result
            try:
                raw_status = call_result.get('status', 'success') if call_result.get('success', False) else 'failed'
                mapped_status = map_status_to_db_enum(raw_status)
                
                if not mapped_status:  # Validar que el mapeo funcionó
                    mapped_status = 'completed'  # Valor por defecto seguro
                    logger.warning(f"Lead {lead_id} - Mapeo de status falló, usando 'completed'")
            except Exception as e:
                logger.error(f"Lead {lead_id} - Error mapeando status: {e}")
                mapped_status = 'completed'  # Valor por defecto seguro
            
            update_fields = {
                'call_status': mapped_status,  # Usar status mapeado correctamente
                'last_call_attempt': 'NOW()',
                'updated_at': 'CURRENT_TIMESTAMP'
            }
            
            # Procesar información de cita si está disponible - VERSIÓN SEGURA
            try:
                if (pearl_response and 
                    isinstance(pearl_response, dict) and 
                    'collectedInfo' in pearl_response and 
                    pearl_response['collectedInfo'] is not None):
                    
                    collected_info = pearl_response['collectedInfo']
                    logger.info(f"Procesando collectedInfo para lead {lead_id}: {collected_info}")
                else:
                    logger.debug(f"Lead {lead_id} - Sin collectedInfo válido, saltando procesamiento de citas")
                    collected_info = None
            except Exception as e:
                logger.error(f"Lead {lead_id} - Error accediendo a collectedInfo: {e}")
                collected_info = None
            
            if collected_info:
                
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
                # Validar que ningún valor sea None
                if value is None:
                    logger.error(f"Lead {lead_id} - Campo {field} es None, saltando")
                    continue
                    
                # Convertir valor a string para comparaciones
                try:
                    value_str = str(value)
                except Exception as e:
                    logger.error(f"Lead {lead_id} - Error convirtiendo {field} a string: {e}")
                    continue
                
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
                    try:
                        clean_value = value_str.strip("'\"") if isinstance(value, str) else value
                        query_params.append(clean_value)
                        logger.info(f"Lead {lead_id} - Campo {field}: valor='{clean_value}', tipo={type(clean_value)}")
                    except Exception as e:
                        logger.error(f"Lead {lead_id} - Error procesando valor para {field}: {e}")
                        continue
            
            # Validar que tenemos al menos un campo para actualizar
            if not set_clauses:
                logger.error(f"Lead {lead_id} - No hay campos válidos para actualizar")
                return False
            
            # Agregar el lead_id al final
            query_params.append(lead_id)
            
            sql = f"UPDATE leads SET {', '.join(set_clauses)} WHERE id = %s"
            
            # Debug logging para identificar el problema
            logger.info(f"Lead {lead_id} - SQL generado: {sql}")
            logger.info(f"Lead {lead_id} - Parámetros: {tuple(query_params)}")
            logger.info(f"Lead {lead_id} - Update fields: {update_fields}")
            
            try:
                cursor.execute(sql, tuple(query_params))
                conn.commit()
                
                if update_fields.get('cita') or update_fields.get('status_level_1'):
                    logger.info(f"Lead {lead_id} procesado exitosamente con información de cita")
                else:
                    logger.info(f"Lead {lead_id} marcado como llamada exitosa (sin información de cita)")
                    
                return True
                    
            except Exception as sql_error:
                logger.error(f"Lead {lead_id} - Error SQL: {sql_error}")
                logger.error(f"Lead {lead_id} - SQL: {sql}")
                logger.error(f"Lead {lead_id} - Params: {tuple(query_params)}")
                conn.rollback()
                return False
            
    except Exception as e:
        logger.error(f"Error marcando llamada exitosa para lead {lead_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass  # Ignorar errores en rollback
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass  # Ignorar errores al cerrar conexión

def get_leads_from_scheduler(limit: int = 10) -> list:
    """
    Obtiene leads que están programados por el scheduler para llamar ahora.
    """
    from call_scheduler import get_next_scheduled_calls
    calls = get_next_scheduled_calls(limit)
    logger.debug(f"[INTEGRATOR] get_next_scheduled_calls returned {len(calls)} calls: {calls}")
    return calls

def integrate_scheduler_with_call_manager():
    """
    Función para integrar el scheduler con el call manager existente.
    
    Esta función puede ser llamada desde el call_manager para usar
    automáticamente las llamadas programadas por el scheduler.
    """
    try:
        # Obtener llamadas pendientes del scheduler
        scheduled_calls = get_leads_from_scheduler(50)
        logger.debug(f"[INTEGRATOR] Scheduled calls fetched: {scheduled_calls}")
        
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
    enhanced_process_call_result(lead_id, result, None, telefono=phone)

def on_call_failed_callback(lead_id: int, phone: str, result: Dict):
    """Callback para cuando falla una llamada."""
    enhanced_process_call_result(lead_id, result)

# Funciones de utilidad para monitoreo
def get_scheduler_integration_stats():
    """Obtiene estadísticas de la integración scheduler-call_manager."""
    conn = get_pymysql_connection()
    if not conn:
        return {}
    
    try:
        with conn.cursor() as cursor:
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
    
    conn = get_pymysql_connection()
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
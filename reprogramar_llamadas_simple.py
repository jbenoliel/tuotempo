#!/usr/bin/env python3
"""
Versión simplificada y segura de reprogramación de llamadas fallidas
para reemplazar temporalmente schedule_failed_call
"""
import logging
import pymysql
from datetime import datetime, timedelta
from config import settings

logger = logging.getLogger(__name__)

def get_pymysql_connection():
    """Obtiene conexión usando pymysql en lugar de mysql.connector"""
    try:
        return pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        logger.error(f"Error conectando con pymysql: {e}")
        return None

def get_retry_config_from_db(outcome: str) -> dict:
    """
    Obtiene la configuración de reintentos desde scheduler_config.
    
    Args:
        outcome: Resultado de la llamada
        
    Returns:
        dict: {'delay_hours': int, 'max_attempts': int}
    """
    default_config = {'delay_hours': 4, 'max_attempts': 3}
    
    conn = None
    try:
        conn = get_pymysql_connection()
        if not conn:
            logger.warning("No se pudo conectar para leer scheduler_config, usando defaults")
            return default_config
            
        with conn.cursor() as cursor:
            # Buscar configuración específica para delay_hours
            cursor.execute("""
                SELECT config_value
                FROM scheduler_config 
                WHERE config_key = %s
                LIMIT 1
            """, (f'{outcome}_delay_hours',))
            
            delay_result = cursor.fetchone()
            delay_hours = int(delay_result[0]) if delay_result else default_config['delay_hours']
            
            # Buscar configuración específica para max_attempts
            cursor.execute("""
                SELECT config_value
                FROM scheduler_config 
                WHERE config_key = %s
                LIMIT 1
            """, (f'{outcome}_max_attempts',))
            
            attempts_result = cursor.fetchone()
            max_attempts = int(attempts_result[0]) if attempts_result else default_config['max_attempts']
            
            # Si no hay config específica, usar defaults generales
            if not delay_result:
                cursor.execute("""
                    SELECT config_value
                    FROM scheduler_config 
                    WHERE config_key = 'default_delay_hours'
                    LIMIT 1
                """)
                default_delay = cursor.fetchone()
                delay_hours = int(default_delay[0]) if default_delay else default_config['delay_hours']
            
            if not attempts_result:
                cursor.execute("""
                    SELECT config_value
                    FROM scheduler_config 
                    WHERE config_key = 'default_max_attempts'
                    LIMIT 1
                """)
                default_attempts = cursor.fetchone()
                max_attempts = int(default_attempts[0]) if default_attempts else default_config['max_attempts']
            
            return {
                'delay_hours': delay_hours,
                'max_attempts': max_attempts
            }
            
    except Exception as e:
        logger.error(f"Error leyendo scheduler_config: {type(e).__name__}: {str(e)}")
        return default_config
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def simple_reschedule_failed_call(lead_id: int, outcome: str) -> bool:
    """
    Versión simplificada de reprogramación de llamadas fallidas.
    
    Args:
        lead_id: ID del lead
        outcome: Resultado ('no_answer', 'busy', 'hang_up')
    
    Returns:
        bool: True si se reprogramó, False si se cerró
    """
    if not lead_id or not isinstance(lead_id, int):
        logger.error(f"Invalid lead_id: {lead_id}")
        return False
    
    if not outcome:
        outcome = 'unknown'
        
    # Leer configuración desde scheduler_config
    config = get_retry_config_from_db(outcome)
    logger.info(f"Lead {lead_id} - Config para '{outcome}': {config}")
    
    conn = None
    try:
        conn = get_pymysql_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD")
            return False
            
        with conn.cursor() as cursor:
            # Obtener información del lead
            cursor.execute("""
                SELECT id, call_attempts_count, lead_status, telefono, nombre
                FROM leads 
                WHERE id = %s
            """, (lead_id,))
            
            lead = cursor.fetchone()
            if not lead:
                logger.error(f"Lead {lead_id} no encontrado")
                return False
                
            if lead['lead_status'] == 'closed':
                logger.info(f"Lead {lead_id} ya está cerrado")
                return False
            
            current_attempts = lead['call_attempts_count'] or 0
            
            # Si excede intentos máximos, cerrar el lead
            if current_attempts >= config['max_attempts']:
                logger.info(f"Lead {lead_id} cerrado por máximo intentos ({current_attempts}/{config['max_attempts']})")
                
                cursor.execute("""
                    UPDATE leads SET
                        lead_status = 'closed',
                        closure_reason = 'Maximo intentos alcanzado',
                        selected_for_calling = FALSE,
                        updated_at = NOW()
                    WHERE id = %s
                """, (lead_id,))
                
                conn.commit()
                return False
            
            # Calcular próximo intento
            next_attempt = datetime.now() + timedelta(hours=config['delay_hours'])
            
            # Incrementar intentos y programar próximo intento
            cursor.execute("""
                UPDATE leads SET
                    call_attempts_count = %s,
                    last_call_attempt = NOW(),
                    call_status = 'no_selected',
                    selected_for_calling = FALSE,
                    updated_at = NOW()
                WHERE id = %s
            """, (current_attempts + 1, lead_id))
            
            # Insertar en call_schedule si la tabla existe
            try:
                cursor.execute("""
                    INSERT INTO call_schedule (lead_id, scheduled_at, attempt_number, status, last_outcome, created_at)
                    VALUES (%s, %s, %s, 'pending', %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        scheduled_at = VALUES(scheduled_at),
                        attempt_number = VALUES(attempt_number),
                        last_outcome = VALUES(last_outcome),
                        updated_at = NOW()
                """, (lead_id, next_attempt, current_attempts + 1, outcome))
            except Exception as e:
                logger.warning(f"No se pudo insertar en call_schedule para lead {lead_id}: {e}")
                # Continuar sin fallar si la tabla no existe
            
            conn.commit()
            
            logger.info(f"Lead {lead_id} reprogramado para {next_attempt} (intento {current_attempts + 1}/{config['max_attempts']})")
            return True
            
    except Exception as e:
        logger.error(f"Error en reprogramación simple para lead {lead_id}: {type(e).__name__}: {str(e)}")
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

def test_simple_reschedule():
    """Función de prueba"""
    print("Probando reprogramación simple...")
    result = simple_reschedule_failed_call(3, 'no_answer')
    print(f"Resultado: {result}")

if __name__ == "__main__":
    test_simple_reschedule()
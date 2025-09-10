"""
Módulo para la actualización periódica de los estados de las llamadas desde la API de Pearl AI.
Este script se ejecuta en segundo plano para sincronizar la base de datos local con los datos de Pearl.
"""

import os
import logging
import json
from datetime import datetime, timedelta, timezone
import time
from dotenv import load_dotenv

from db import get_connection
from pearl_caller import get_pearl_client, PearlAPIError

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def insert_call_record(cursor, call_details: dict, lead_id: int, outbound_id: str) -> bool:
    """
    Inserta un registro detallado de la llamada en la tabla pearl_calls.
    
    Args:
        cursor: Cursor de la base de datos
        call_details: Detalles completos de la llamada de Pearl AI
        lead_id: ID del lead asociado
        outbound_id: ID de la campaña outbound
        
    Returns:
        bool: True si la inserción fue exitosa
    """
    try:
        # Verificar si la llamada ya existe para evitar duplicados
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE call_id = %s", (call_details.get('id'),))
        if cursor.fetchone()[0] > 0:
            logger.debug(f"Llamada {call_details.get('id')} ya existe en pearl_calls, actualizando...")
            return update_call_record(cursor, call_details, lead_id, outbound_id)
        
        # Obtener número de teléfono de call_details
        phone_number = call_details.get('to') or call_details.get('phoneNumber') or call_details.get('callData', {}).get('telefono')
        
        # Preparar datos para inserción con formato corregido
        call_data = {
            'call_id': call_details.get('id'),
            'phone_number': phone_number,
            'lead_id': lead_id,
            'outbound_id': outbound_id,
            'call_time': convert_pearl_datetime(call_details.get('startTime')),
            'start_time': convert_pearl_datetime(call_details.get('startTime')),
            'end_time': convert_pearl_datetime(call_details.get('endTime')),
            'duration': call_details.get('duration'),
            'status': str(call_details.get('status', ''))[:50],  # Limitar longitud
            'outcome': str(call_details.get('outcome', call_details.get('status', '')))[:100],
            'summary': call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary'),
            'transcription': call_details.get('transcription'),
            'recording_url': call_details.get('recordingUrl'),
            'collected_info': json.dumps(call_details.get('callData', {})),
            'cost': call_details.get('cost')
        }
        
        # Filtrar valores None para evitar problemas con campos NOT NULL
        call_data = {k: v for k, v in call_data.items() if v is not None}
        
        # Crear query de inserción dinámico
        columns = ', '.join(call_data.keys())
        placeholders = ', '.join(['%s'] * len(call_data))
        
        insert_sql = f"""
            INSERT INTO pearl_calls ({columns})
            VALUES ({placeholders})
        """
        
        cursor.execute(insert_sql, tuple(call_data.values()))
        
        logger.info(f"📞 Registro de llamada insertado: {call_details.get('id')} -> Lead {lead_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error insertando registro de llamada {call_details.get('id')}: {e}")
        return False

def update_call_record(cursor, call_details: dict, lead_id: int, outbound_id: str) -> bool:
    """
    Actualiza un registro existente de llamada en pearl_calls.
    """
    try:
        update_data = {
            'phone_number': call_details.get('to') or call_details.get('phoneNumber') or call_details.get('callData', {}).get('telefono'),
            'lead_id': lead_id,
            'outbound_id': outbound_id,
            'call_time': convert_pearl_datetime(call_details.get('startTime')),
            'start_time': convert_pearl_datetime(call_details.get('startTime')),
            'end_time': convert_pearl_datetime(call_details.get('endTime')),
            'duration': call_details.get('duration'),
            'status': str(call_details.get('status', ''))[:50],
            'outcome': str(call_details.get('outcome', call_details.get('status', '')))[:100],
            'summary': call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary'),
            'transcription': call_details.get('transcription'),
            'recording_url': call_details.get('recordingUrl'),
            'collected_info': json.dumps(call_details.get('callData', {})),
            'cost': call_details.get('cost')
        }
        
        # Filtrar valores None
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if update_data:
            set_clause = ', '.join([f"{k} = %s" for k in update_data.keys()])
            update_sql = f"UPDATE pearl_calls SET {set_clause} WHERE call_id = %s"
            
            cursor.execute(update_sql, tuple(update_data.values()) + (call_details.get('id'),))
            logger.info(f"📞 Registro de llamada actualizado: {call_details.get('id')}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error actualizando registro de llamada {call_details.get('id')}: {e}")
        return False

def get_last_sync_time(db_conn) -> datetime:
    """
    Obtiene la marca de tiempo de la última llamada actualizada en la base de datos.
    Si no hay ninguna, devuelve una fecha por defecto (24 horas atrás).
    """
    try:
        cursor = db_conn.cursor(dictionary=True)
        # Buscamos el call_time más reciente que no sea nulo
        cursor.execute("SELECT MAX(call_time) as last_call FROM leads WHERE call_time IS NOT NULL")
        result = cursor.fetchone()
        cursor.close()
        
        if result and result['last_call']:
            # Asegurarse de que la fecha tenga timezone para la comparación
            return result['last_call'].replace(tzinfo=timezone.utc)
        else:
            # Si no hay llamadas, empezamos desde hace 7 días para asegurar que capturamos todas
            logger.info("No se encontró una última sincronización. Se usarán los últimos 7 días.")
            return datetime.now(timezone.utc) - timedelta(days=7)
    except Exception as e:
        logger.error(f"Error al obtener el último tiempo de sincronización: {e}")
        # Fallback seguro en caso de error
        return datetime.now(timezone.utc) - timedelta(days=7)

def update_calls_from_pearl():
    """Función principal que se encarga de obtener y actualizar las llamadas."""
    logger.info("🚀 Iniciando ciclo de actualización de llamadas de Pearl AI...")
    
    try:
        pearl_client = get_pearl_client()
        outbound_id = pearl_client.get_default_outbound_id()
        if not outbound_id:
            logger.error("PEARL_OUTBOUND_ID no está configurado. El actualizador no puede continuar.")
            return
    except PearlAPIError as e:
        logger.error(f"Error al inicializar el cliente de Pearl: {e}")
        return

    db_conn = None
    try:
        db_conn = get_connection()
        if not db_conn:
            logger.error("No se pudo establecer conexión con la base de datos.")
            return

        # 1. Determinar el rango de fechas para la búsqueda
        from_date_dt = get_last_sync_time(db_conn)
        to_date_dt = datetime.now(timezone.utc)

        # Formato para la API de Pearl (ISO 8601 con 'Z' para UTC)
        from_date_str = from_date_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        to_date_str = to_date_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        # 2. Obtener llamadas de la API de Pearl (con paginación)
        logger.info(f"Buscando llamadas para outbound {outbound_id} desde {from_date_str} hasta {to_date_str}")
        all_calls = []
        skip = 0
        limit = 100  # Máximo permitido por Pearl AI
        
        while True:
            try:
                # Obtener página de llamadas
                response_data = pearl_client.search_calls_paginated(outbound_id, from_date_str, to_date_str, skip, limit)
                
                if isinstance(response_data, dict):
                    total_count = response_data.get('count', 0)
                    page_calls = response_data.get('results', [])
                else:
                    page_calls = response_data if isinstance(response_data, list) else []
                    total_count = len(page_calls)
                
                if not page_calls:
                    break
                    
                all_calls.extend(page_calls)
                logger.info(f"Obtenidas {len(page_calls)} llamadas (página {skip//limit + 1}). Total: {len(all_calls)}/{total_count}")
                
                # Si obtenimos menos del límite, es la última página
                if len(page_calls) < limit:
                    break
                    
                skip += limit
                
                # Seguridad: no más de 20 páginas (2000 llamadas)
                if skip >= 2000:
                    logger.warning("Límite de paginación alcanzado (2000 llamadas)")
                    break
                    
            except PearlAPIError as e:
                logger.error(f"Error al buscar llamadas en la API de Pearl (skip={skip}): {e}")
                break

        calls = all_calls
        if not calls:
            logger.info("No se encontraron nuevas llamadas para actualizar.")
            return

        # 3. Actualizar la base de datos con las llamadas obtenidas
        logger.info(f"✅ Encontradas {len(calls)} llamadas. Procesando...")
        updated_count = 0
        cursor = db_conn.cursor()

        for call_item in calls:
            call_details = None
            lead_id = None
            try:
                # Si la API devuelve solo IDs, obtenemos los detalles completos
                if isinstance(call_item, str):
                    logger.info(f"Elemento es un ID de llamada ('{call_item}'). Obteniendo detalles...")
                    call_details = pearl_client.get_call_status(call_item)
                elif isinstance(call_item, dict):
                    call_details = call_item
                else:
                    logger.warning(f"Elemento desconocido en la respuesta de la API: {call_item}")
                    continue

                if not call_details:
                    logger.warning(f"No se pudieron obtener detalles para la llamada: {call_item}")
                    continue

                # Buscar lead_id por teléfono en lugar de por campo 'orden'
                phone_number = call_details.get('to')
                if not phone_number:
                    logger.debug(f"Llamada con ID {call_details.get('id')} no tiene teléfono. Se omite.")
                    continue
                
                # Normalizar teléfono: quitar +34 y espacios para buscar en BD
                phone_normalized = phone_number.replace('+34', '').replace(' ', '').replace('-', '')
                
                # Buscar el lead por teléfono normalizado
                cursor.execute("SELECT id FROM leads WHERE telefono = %s LIMIT 1", (phone_normalized,))
                lead_result = cursor.fetchone()
                
                if not lead_result:
                    logger.debug(f"No se encontró lead para el teléfono {phone_number} (normalizado: {phone_normalized}) en llamada {call_details.get('id')}. Se omite.")
                    continue
                    
                lead_id = lead_result[0]
                logger.info(f"📞 Procesando llamada {call_details.get('id')} para lead {lead_id} (teléfono: {phone_number} -> {phone_normalized})")

                # 1. INSERTAR/ACTUALIZAR EN PEARL_CALLS (registro detallado)
                call_inserted = insert_call_record(cursor, call_details, lead_id, outbound_id)
                
                # 2. PROCESAR RESULTADO CON EL SCHEDULER INTEGRADO
                try:
                    from call_manager_scheduler_integration import enhanced_process_call_result
                    
                    # Mapear el resultado de Pearl AI al formato esperado por enhanced_process_call_result
                    pearl_status = call_details.get('status')
                    call_result = {
                        'success': pearl_status == 4,  # 4 = Completed/Success
                        'status': map_pearl_status_to_result(None, pearl_status),
                        'duration': call_details.get('duration', 0),
                        'error_message': get_error_message_from_pearl_status(None, pearl_status),
                        'lead_id': lead_id,
                        'phone_number': call_details.get('to')
                    }
                    
                    # Procesar el resultado con la integración del scheduler
                    enhanced_process_call_result(lead_id, call_result, call_details)
                    
                    updated_count += 1
                    logger.info(f"✅ COMPLETO - Lead {lead_id} procesado con scheduler integration para llamada {call_details.get('id')}")
                    
                except ImportError:
                    logger.warning("⚠️ Módulo de integración scheduler no disponible, usando método básico")
                    
                    # Fallback al método original
                    update_data = {
                        'call_id': call_details.get('id'),
                        'call_time': convert_pearl_datetime(call_details.get('startTime')),
                        'call_status': str(call_details.get('status', ''))[:50],
                        'call_duration': call_details.get('duration'),
                        'call_summary': call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary'),
                        'call_recording_url': call_details.get('recordingUrl'),
                        'pearl_call_response': json.dumps(call_details) if call_details else None,
                        'updated_at': datetime.now()
                    }

                    update_fields = {k: v for k, v in update_data.items() if v is not None}
                    
                    if update_fields:
                        set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
                        sql = f"UPDATE leads SET {set_clause} WHERE id = %s"
                        params = list(update_fields.values()) + [lead_id]
                        cursor.execute(sql, tuple(params))
                        
                    if cursor.rowcount > 0 or call_inserted:
                        updated_count += 1
                        status_msg = "✅ COMPLETO" if call_inserted else "⚠️ PARCIAL (solo leads)"
                        logger.info(f"{status_msg} - Lead {lead_id} procesado con llamada {call_details.get('id')}")
                        
                except Exception as e:
                    logger.error(f"❌ Error en integración scheduler para lead {lead_id}: {e}")
                    # Continuar con el procesamiento básico en caso de error

            except Exception as e:
                call_id_log = call_details.get('id') if call_details else call_item
                logger.error(f"Error procesando la llamada {call_id_log} para el lead {lead_id}: {e}")

        db_conn.commit()
        cursor.close()
        logger.info(f"✅ Proceso de actualización finalizado. {updated_count} leads actualizados de {len(calls)} llamadas recibidas.")

    except Exception as e:
        logger.error(f"Error inesperado en el proceso de actualización de llamadas: {e}")
        if db_conn:
            db_conn.rollback()
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            logger.info("Conexión a la base de datos cerrada.")

def run_scheduler():
    """Ejecuta el actualizador en un bucle infinito con un retardo de 60 segundos."""
    while True:
        update_calls_from_pearl()
        logger.info("Esperando 60 segundos para el próximo ciclo de actualización...")
        time.sleep(60)

def convert_pearl_datetime(datetime_str: str) -> str:
    """
    Convierte datetime de Pearl AI (formato ISO con Z) a formato MySQL.
    Ejemplo: '2025-09-09T10:26:47.961Z' -> '2025-09-09 10:26:47'
    """
    if not datetime_str:
        return None
    
    try:
        # Remover la 'Z' y microsegundos si existen
        dt_clean = datetime_str.replace('Z', '').split('.')[0]
        # Convertir T a espacio para MySQL
        mysql_datetime = dt_clean.replace('T', ' ')
        return mysql_datetime
    except Exception as e:
        logger.warning(f"Error convirtiendo datetime {datetime_str}: {e}")
        return None

def map_pearl_status_to_result(conversation_status: int, status: int) -> str:
    """
    Mapea los códigos de estado de Pearl AI a strings comprensibles.
    
    conversationStatus:
    - 1: New
    - 10: Need Retry
    - 100: Success
    - 110: Not Successful  
    - 130: Completed
    - 150: Unreachable
    """
    # Pearl AI status oficial (documentación):
    # 3 - InProgress
    # 4 - Completed (EXITOSA)
    # 5 - Busy (OCUPADO - REPROGRAMAR)
    # 6 - Failed (FALLO - REPROGRAMAR) 
    # 7 - NoAnswer (NO CONTESTA - REPROGRAMAR)
    # 8 - Cancelled
    
    if status == 4:
        return 'success'  # Completed - Exitosa
    elif status == 5:
        return 'busy'  # Busy - REPROGRAMAR
    elif status == 6:
        return 'error'  # Failed - REPROGRAMAR  
    elif status == 7:
        return 'no_answer'  # NoAnswer - REPROGRAMAR
    elif status == 3:
        return 'in_progress'  # InProgress
    elif status == 8:
        return 'cancelled'  # Cancelled
    else:
        return f'unknown_status_{status}'

def get_error_message_from_pearl_status(conversation_status: int, status: int) -> str:
    """
    Genera un mensaje de error basado en los códigos de estado de Pearl AI.
    """
    # Mapear status oficiales de Pearl AI
    status_messages = {
        3: "Llamada en progreso",
        4: None,  # Completed - success, no error message
        5: "Línea ocupada",
        6: "Llamada fallida", 
        7: "No contesta",
        8: "Llamada cancelada"
    }
    
    return status_messages.get(status, f"Estado desconocido: status={status}")

if __name__ == "__main__":
    logger.info("Iniciando el scheduler de actualización de llamadas en modo standalone.")
    run_scheduler()

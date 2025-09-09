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
        
        # Obtener número de teléfono de call_details o del lead
        phone_number = call_details.get('phoneNumber') or call_details.get('callData', {}).get('telefono')
        
        # Preparar datos para inserción
        call_data = {
            'call_id': call_details.get('id'),
            'phone_number': phone_number,
            'lead_id': lead_id,
            'outbound_id': outbound_id,
            'call_time': call_details.get('startTime'),
            'start_time': call_details.get('startTime'),
            'end_time': call_details.get('endTime'),
            'duration': call_details.get('duration'),
            'status': call_details.get('status'),
            'outcome': call_details.get('outcome', call_details.get('status')),
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
            'phone_number': call_details.get('phoneNumber') or call_details.get('callData', {}).get('telefono'),
            'lead_id': lead_id,
            'outbound_id': outbound_id,
            'call_time': call_details.get('startTime'),
            'start_time': call_details.get('startTime'),
            'end_time': call_details.get('endTime'),
            'duration': call_details.get('duration'),
            'status': call_details.get('status'),
            'outcome': call_details.get('outcome', call_details.get('status')),
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
            # Si no hay llamadas, empezamos desde hace 24 horas
            logger.info("No se encontró una última sincronización. Se usarán las últimas 24 horas.")
            return datetime.now(timezone.utc) - timedelta(days=1)
    except Exception as e:
        logger.error(f"Error al obtener el último tiempo de sincronización: {e}")
        # Fallback seguro en caso de error
        return datetime.now(timezone.utc) - timedelta(days=1)

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

        # 2. Obtener llamadas de la API de Pearl
        logger.info(f"Buscando llamadas para outbound {outbound_id} desde {from_date_str} hasta {to_date_str}")
        try:
            response_data = pearl_client.search_calls(outbound_id, from_date_str, to_date_str)
        except PearlAPIError as e:
            logger.error(f"Error al buscar llamadas en la API de Pearl: {e}")
            return # No continuar si la API falla

        # La API devuelve un dict con 'count' y 'results'. Usamos 'results'.
        calls = []
        if isinstance(response_data, dict) and 'results' in response_data:
            calls = response_data.get('results', [])
        elif isinstance(response_data, list):
            # Si en el futuro la API devuelve una lista directamente, también funcionará
            calls = response_data

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

                lead_id = call_details.get('callData', {}).get('orden')
                if not lead_id:
                    logger.debug(f"Llamada con ID {call_details.get('id')} no tiene 'orden' (lead_id) - llamada externa. Se omite.")
                    continue

                # 1. INSERTAR/ACTUALIZAR EN PEARL_CALLS (registro detallado)
                call_inserted = insert_call_record(cursor, call_details, lead_id, outbound_id)
                
                # 2. ACTUALIZAR EN LEADS (resumen en tabla principal)
                update_data = {
                    'call_id': call_details.get('id'),
                    'call_time': call_details.get('startTime'),
                    'call_status': call_details.get('status'),
                    'call_duration': call_details.get('duration'),
                    'call_summary': call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary'),
                    'call_recording_url': call_details.get('recordingUrl'),
                    'pearl_call_response': json.dumps(call_details) if call_details else None,
                    'updated_at': datetime.now()
                }

                # Filtrar valores nulos para no sobrescribir datos existentes con nada
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

if __name__ == "__main__":
    logger.info("Iniciando el scheduler de actualización de llamadas en modo standalone.")
    run_scheduler()

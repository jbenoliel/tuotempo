"""
Gestor de cola y estado de llamadas automáticas.
Maneja la lógica de negocio para procesar leads, gestionar la cola de llamadas
y coordinar con la API de Pearl AI.
"""

import os
import threading
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from queue import Queue, Empty
from dataclasses import dataclass
from enum import Enum

from pearl_caller import get_pearl_client, PearlAPIError
from db import get_connection

# Configurar logging
logger = logging.getLogger(__name__)

# Global variable for override phone number
_override_phone: Optional[str] = os.getenv("TEST_CALL_PHONE")

def set_override_phone(phone: Optional[str]):
    """Allows setting or clearing the override phone number."""
    global _override_phone
    _override_phone = phone.strip() if phone else None
    logger.info(f"Override phone set to: {_override_phone}")

def get_override_phone() -> Optional[str]:
    """Returns the current override phone number."""
    global _override_phone
    return _override_phone

def normalize_spanish_phone(phone: str) -> str:
    """Normaliza un teléfono español añadiendo +34 si es necesario."""
    if not phone:
        return phone
        
    # Limpiar el teléfono de espacios y caracteres extra
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Si ya tiene el prefijo +34, devolverlo como está
    if phone.startswith('+34'):
        return phone
    
    # Si tiene 34 al principio (sin +), añadir el +
    if clean_phone.startswith('34') and len(clean_phone) == 11:
        return '+' + clean_phone
    
    # Si es un teléfono de 9 dígitos (formato español), añadir +34
    if len(clean_phone) == 9:
        return '+34' + clean_phone
    
    # Si tiene 8 dígitos, probablemente le falta el primer 6/7/9
    if len(clean_phone) == 8:
        # Asumir que es un móvil que empieza por 6
        return '+346' + clean_phone
    
    # En cualquier otro caso, devolver tal como está
    logger.warning(f"Teléfono con formato inesperado: {phone} -> {clean_phone}")
    return phone


class CallStatus(Enum):
    QUEUED = "selected"        # Mapea a 'selected' en BD
    IN_PROGRESS = "calling"    # Mapea a 'calling' en BD  
    COMPLETED = "completed"    # Mapea a 'completed' en BD
    FAILED = "error"           # Mapea a 'error' en BD
    NO_ANSWER = "no_answer"    # Mapea a 'no_answer' en BD
    BUSY = "busy"              # Mapea a 'busy' en BD


@dataclass
class CallTask:
    lead_id: int
    phone_number: str
    lead_data: Dict


class CallManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(CallManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, app=None, pearl_client=None, on_status_update: Optional[Callable] = None):
        if not hasattr(self, '_initialized'):
            self.app = app
            self.pearl_client = pearl_client if pearl_client else get_pearl_client()
            self.on_status_update = on_status_update
            self.call_queue = Queue()
            self.is_running = False
            self.workers: List[threading.Thread] = []
            self.active_calls = {}
            self.max_concurrent_calls = 3
            self.current_session_id: Optional[int] = None
            self.on_stats_updated = None
            self.stats = {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'no_answer': 0,
                'busy': 0,
                'in_progress': 0
            }
            self._initialized = True
            logger.info("CallManager initialized")

    def set_config(self, max_concurrent_calls: int):
        self.max_concurrent_calls = max_concurrent_calls
        logging.info(f"Max concurrent calls set to: {max_concurrent_calls}")

    def set_callbacks(self, on_call_started=None, on_call_completed=None, on_call_failed=None, on_stats_updated=None):
        """Configura callbacks para eventos del sistema de llamadas."""
        self.on_call_started = on_call_started
        self.on_call_completed = on_call_completed  
        self.on_call_failed = on_call_failed
        self.on_stats_updated = on_stats_updated
        logger.info("Callbacks configurados para CallManager")

    def start_calling(self, specific_lead_ids: List[int] = None) -> bool:
        """
        Inicia el sistema de llamadas.
        
        Args:
            specific_lead_ids: Lista de IDs específicos para llamar. Si es None, usa todos los marcados.
        """
        if self.is_running:
            logger.warning("El sistema de llamadas ya está ejecutándose")
            return False
            
        try:
            # Obtener leads seleccionados de la BD
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if specific_lead_ids:
                # Llamar solo a leads específicos
                placeholders = ','.join(['%s'] * len(specific_lead_ids))
                query = f"""
                    SELECT id, nombre, apellidos, telefono, telefono2
                    FROM leads 
                    WHERE id IN ({placeholders})
                      AND (manual_management IS NULL OR manual_management = FALSE)
                      AND ((telefono IS NOT NULL AND telefono != '') 
                           OR (telefono2 IS NOT NULL and telefono2 != ''))
                """
                cursor.execute(query, specific_lead_ids)
                logger.info(f"🎯 Usando leads específicos: {specific_lead_ids}")
            else:
                # Fallback al comportamiento anterior (todos los marcados)
                cursor.execute("""
                    SELECT id, nombre, apellidos, telefono, telefono2
                    FROM leads 
                    WHERE selected_for_calling = TRUE
                      AND (manual_management IS NULL OR manual_management = FALSE)
                      AND ((telefono IS NOT NULL AND telefono != '') 
                           OR (telefono2 IS NOT NULL AND telefono2 != ''))
                """)
                logger.info("📋 Usando todos los leads marcados como selected_for_calling=TRUE")
            
            leads = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not leads:
                if specific_lead_ids:
                    logger.warning(f"No se encontraron leads válidos en la lista específica: {specific_lead_ids}")
                else:
                    logger.warning("No hay leads seleccionados para llamar")
                return False
                
            logger.info(f"✅ Iniciando llamadas para {len(leads)} leads")
            if specific_lead_ids:
                logger.info(f"📞 IDs específicos encontrados: {[lead['id'] for lead in leads]}")
            self.is_running = True
            
            # Procesar cada lead con teléfonos normalizados
            for lead in leads:
                # VERIFICACIÓN MODO PRUEBA - LOGS DETALLADOS
                logger.info(f"🔍 VERIFICACIÓN MODO PRUEBA - Lead ID: {lead['id']}")
                logger.info(f"📞 Override phone configurado: {_override_phone}")
                logger.info(f"📱 Teléfono original del lead: {lead.get('telefono', 'N/A')}")
                logger.info(f"📱 Teléfono secundario del lead: {lead.get('telefono2', 'N/A')}")
                
                # Determinar qué teléfono usar - APLICAR OVERRIDE
                if _override_phone:
                    phone_to_use = _override_phone
                    logger.warning(f"🧪 MODO PRUEBA ACTIVO - Usando teléfono override: {phone_to_use}")
                else:
                    phone_to_use = lead['telefono'] if lead['telefono'] else lead['telefono2']
                    logger.info(f"📞 Usando teléfono normal del lead: {phone_to_use}")
                
                # Normalizar el teléfono añadiendo +34 si es necesario
                normalized_phone = normalize_spanish_phone(phone_to_use)
                
                logger.info(f"🎯 Teléfono FINAL normalizado: {normalized_phone}")
                logger.info(f"✅ Procesando lead {lead['id']}: {lead.get('nombre', 'N/A')} - {phone_to_use} -> {normalized_phone}")
                
                # Llamar callbacks si existen
                if self.on_call_started:
                    self.on_call_started(lead['id'], normalized_phone)
                    
                # Ejecutar llamada real con Pearl AI
                logger.info(f"🚀 INICIANDO LLAMADA A PEARL AI")
                logger.info(f"📞 Número final enviado a Pearl: {normalized_phone}")
                outbound_id = self.pearl_client.get_default_outbound_id()
                success, api_response = self.pearl_client.make_call(outbound_id, normalized_phone, lead)

                # Actualizar estadísticas
                if success:
                    self.stats['completed'] += 1
                    call_status = CallStatus.COMPLETED.value
                else:
                    self.stats['failed'] += 1
                    call_status = CallStatus.FAILED.value

                # Registrar intento en la BD
                try:
                    conn_upd = get_connection()
                    cur_upd = conn_upd.cursor()
                    cur_upd.execute("""
                        UPDATE leads
                        SET call_attempts_count = IFNULL(call_attempts_count,0) + 1,
                            last_call_attempt = NOW(),
                            call_status = %s
                        WHERE id = %s
                    """, (call_status, lead['id']))
                    conn_upd.commit()
                    cur_upd.close()
                    conn_upd.close()
                except Exception as db_err:
                    logger.error(f"Error actualizando lead {lead['id']} en BD: {db_err}")

                # Llamar callbacks según resultado
                if success and self.on_call_completed:
                    self.on_call_completed(lead['id'], normalized_phone, api_response)
                elif not success and self.on_call_failed:
                    self.on_call_failed(lead['id'], normalized_phone, api_response)

                # Emitir actualización de stats si corresponde
                if self.on_stats_updated:
                    self.on_stats_updated(self.stats)
            
            logger.info("Sistema de llamadas completado")
            self.is_running = False
            if self.on_stats_updated:
                self.on_stats_updated(self.stats)
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando sistema de llamadas: {e}")
            self.is_running = False
            return False
    
    def stop_calling(self) -> bool:
        """Detiene el sistema de llamadas."""
        if not self.is_running:
            logger.warning("El sistema de llamadas no está ejecutándose")
            return False
            
        self.is_running = False
        logger.info("Sistema de llamadas detenido")
        return True

    def start(self, leads: List[Dict]):
        if self.is_running:
            logging.warning("Call manager is already running.")
            return

        with self.app.app_context():
            new_session = Session()
            db.session.add(new_session)
            db.session.commit()
            self.current_session_id = new_session.id

        self.is_running = True
        self.stats = self.stats.fromkeys(self.stats, 0)
        self.stats['total'] = len(leads)

        for lead_data in leads:
            if self._add_lead_to_queue(lead_data):
                self._update_lead_status(lead_data['id'], 'queued')

        self.workers = []
        for i in range(self.max_concurrent_calls):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Call manager started with {len(leads)} leads and {self.max_concurrent_calls} workers.")
        self._emit_status()

    def stop(self):
        if not self.is_running:
            logger.warning("Call manager is not running.")
            return

        self.is_running = False
        # Empty the queue to make workers finish if they are waiting
        while not self.call_queue.empty():
            try:
                self.call_queue.get_nowait()
            except Empty:
                break
        
        # Wait for current workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        self.workers = []
        self.current_session_id = None
        logger.info("Call manager stopped.")
        self._emit_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            'is_running': self.is_running,
            'queue_size': self.call_queue.qsize(),
            'active_calls': self.stats.get('in_progress', 0),
            'stats': self.stats
        }

    def _add_lead_to_queue(self, lead_data: Dict) -> bool:
        # Log detallado para verificar modo de prueba
        logger.info(f"🔍 VERIFICACIÓN MODO PRUEBA - Lead ID: {lead_data['id']}")
        logger.info(f"📞 Override phone configurado: {_override_phone}")
        logger.info(f"📱 Teléfono original del lead: {lead_data.get('telefono', 'N/A')}")
        logger.info(f"📱 Teléfono secundario del lead: {lead_data.get('telefono2', 'N/A')}")
        
        phone = _override_phone if _override_phone else lead_data.get('telefono', '').strip()
        logger.info(f"🎯 Teléfono seleccionado (1ra pasada): {phone}")
        
        if not self.pearl_client.validate_phone_number(phone):
            logger.info(f"❌ Teléfono inválido, probando teléfono2...")
            phone = _override_phone if _override_phone else lead_data.get('telefono2', '').strip()
            logger.info(f"🎯 Teléfono seleccionado (2da pasada): {phone}")

        if self.pearl_client.validate_phone_number(phone):
            logger.info(f"✅ Teléfono FINAL válido: {phone}")
            if _override_phone:
                logger.warning(f"🧪 MODO PRUEBA ACTIVO - Llamando a {phone} en lugar del teléfono real del lead")
            task = CallTask(
                lead_id=lead_data['id'],
                phone_number=phone,
                lead_data=lead_data
            )
            self.call_queue.put(task)
            return True
        else:
            logger.warning(f"Lead {lead_data['id']} has no valid phone number. Skipping.")
            self._update_lead_status(lead_data['id'], 'failed', error_message="Invalid phone number")
            self.stats['failed'] += 1
            return False

    def _worker(self):
        while self.is_running:
            try:
                task = self.call_queue.get(timeout=1)
                self.stats['in_progress'] += 1
                self._emit_status()
                self._process_call(task)
                self.stats['in_progress'] -= 1
                self.call_queue.task_done()
            except Empty:
                if not self.is_running:
                    break
                # If the queue is empty, check for active calls.
                # If none, we can stop the system.
                if self.stats.get('in_progress', 0) == 0 and self.call_queue.empty():
                    logger.info("All calls processed. Stopping manager.")
                    self.stop()
                    break
                continue

    def _process_call(self, task: CallTask):
        lead_id = task.lead_id
        phone_number = task.phone_number
        logger.info(f"Processing call for lead {lead_id} to {phone_number}")
        self._update_lead_status(lead_id, 'in_progress')

        call_id = self._create_call_record(lead_id, phone_number)

        try:
            # Real call logic with PearlClient would go here
            # We simulate the call result for now
            # call_result = self.pearl_client.make_call(phone_number, lead_id)
            time.sleep(5) # Simulate call duration
            call_result = {'status': 'completed', 'duration': 5}

            status = call_result.get('status', 'failed')
            self._update_lead_status(lead_id, status)
            self._update_call_record(call_id, status, call_result.get('duration'))
            
            if status == 'completed':
                self.stats['completed'] += 1
            else:
                self.stats[status] = self.stats.get(status, 0) + 1

        except Exception as e:
            logger.error(f"Error processing call for lead {lead_id}: {e}")
            self._update_lead_status(lead_id, 'failed', error_message=str(e))
            self._update_call_record(call_id, 'failed', duration=0, error_message=str(e))
            self.stats['failed'] += 1
        finally:
            self._emit_status()

    def _update_lead_status(self, lead_id: int, status: str, error_message: Optional[str] = None):
        """
        Actualiza el estado de un lead en la base de datos.
        
        Args:
            lead_id (int): ID del lead
            status (str): Nuevo estado
            error_message (str, optional): Mensaje de error si aplica
        """
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                # Primero verificamos si el lead existe y obtenemos su valor de call_attempts actual
                cursor.execute(
                    "SELECT call_attempts FROM leads WHERE id = %s",
                    (lead_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Incrementamos call_attempts en 1 o establecemos como 1 si es NULL
                    call_attempts = 1 if result[0] is None else result[0] + 1
                    
                    # Actualizamos el estado del lead
                    sql = """
                    UPDATE leads 
                    SET call_status = %s, 
                        last_call_time = %s, 
                        call_attempts = %s
                    """
                    
                    params = [status, datetime.utcnow(), call_attempts]
                    
                    # Añadir mensaje de error si existe
                    if error_message:
                        sql += ", last_call_error = %s"
                        params.append(error_message)
                    
                    sql += " WHERE id = %s"
                    params.append(lead_id)
                    
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    # Si hay callback para notificar actualizaciones, lo llamamos
                    if self.on_status_update:
                        # Obtener datos actualizados para el callback
                        cursor.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
                        lead_data = cursor.fetchone()
                        if lead_data:
                            # Convertir a diccionario usando los nombres de columnas
                            column_names = [desc[0] for desc in cursor.description]
                            lead_dict = dict(zip(column_names, lead_data))
                            self.on_status_update('lead_update', lead_dict)
                            
            conn.close()
        except Exception as e:
            logger.error(f"Error actualizando estado de lead {lead_id}: {e}")
            # Intentar cerrar la conexión en caso de error
            try:
                conn.close()
            except:
                pass

    def _create_call_record(self, lead_id: int, phone_number: str) -> int:
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                # Insertar registro de llamada y obtener el ID generado
                cursor.execute(
                    """INSERT INTO calls (lead_id, session_id, phone_number, status, start_time)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (lead_id, self.current_session_id, phone_number, 'initiated', datetime.utcnow())
                )
                call_id = cursor.fetchone()[0]
                conn.commit()
                conn.close()
                return call_id
        except Exception as e:
            logger.error(f"Error creando registro de llamada para lead {lead_id}: {e}")
            try:
                conn.close()
            except:
                pass
            return -1  # Valor de error

    def _update_call_record(self, call_id: int, status: str, duration: Optional[int] = None, error_message: Optional[str] = None):
        if call_id < 0:  # Omitir actualización si el ID no es válido (caso de error en _create_call_record)
            return
            
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                # Construir la consulta SQL con los campos a actualizar
                sql = "UPDATE calls SET status = %s, end_time = %s"
                params = [status, datetime.utcnow()]
                
                # Añadir duración si está disponible
                if duration is not None:
                    sql += ", duration_seconds = %s"
                    params.append(duration)
                    
                # Añadir mensaje de error si existe
                if error_message:
                    sql += ", error_message = %s"
                    params.append(error_message)
                    
                # Completar la consulta con la condición WHERE
                sql += " WHERE id = %s"
                params.append(call_id)
                
                # Ejecutar la actualización
                cursor.execute(sql, params)
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Error actualizando registro de llamada {call_id}: {e}")
            try:
                conn.close()
            except:
                pass

    def _emit_status(self):
        if self.on_status_update:
            self.on_status_update('status_update', self.get_status())            
            # Callback de estadísticas
            if self.on_stats_updated:
                try:
                    self.on_stats_updated(self.stats.copy())
                except Exception as e:
                    logger.error(f"Error en callback on_stats_updated: {e}")

    
    # Método duplicado eliminado
    
    def _update_lead_call_data(self, lead_id: int, response_data: Dict):
        """
        Actualiza los datos de llamada de un lead.
        
        Args:
            lead_id (int): ID del lead
            response_data (Dict): Respuesta de la API de Pearl
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Extraer datos relevantes
            call_id = response_data.get('callId') or response_data.get('id')
            pearl_response = json.dumps(response_data)
            
            query = """
                UPDATE leads SET 
                    call_id = %s,
                    pearl_call_response = %s,
                    call_time = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            cursor.execute(query, [call_id, pearl_response, datetime.now(), lead_id])
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error actualizando datos de llamada para lead {lead_id}: {e}")
        finally:
            if conn:
                conn.close()
    
    def _increment_call_attempts(self, lead_id: int):
        """
        Incrementa el contador de intentos de llamada.
        
        Args:
            lead_id (int): ID del lead
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            query = """
                UPDATE leads SET 
                    call_attempts_count = COALESCE(call_attempts_count, 0) + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            cursor.execute(query, [lead_id])
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error incrementando intentos para lead {lead_id}: {e}")
        finally:
            if conn:
                conn.close()
    
    def _cleanup_completed_calls(self):
        """
        Limpia llamadas completadas del diccionario de llamadas activas.
        """
        completed_leads = []
        
        for lead_id, call_info in self.active_calls.items():
            if not call_info['thread'].is_alive():
                completed_leads.append(lead_id)
        
        for lead_id in completed_leads:
            del self.active_calls[lead_id]
    
    def _cleanup_active_calls(self):
        """
        Limpia y actualiza estado de todas las llamadas activas al detener.
        """
        for lead_id, call_info in self.active_calls.items():
            if call_info['thread'].is_alive():
                # No podemos forzar parar el thread, pero actualizamos el estado
                logger.warning(f"Llamada activa para lead {lead_id} al detener gestor")
                self._update_lead_status(lead_id, CallStatus.ERROR, "Proceso interrumpido")
        
        self.active_calls.clear()
    
    def reset_stats(self):
        """Reinicia las estadísticas."""
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "busy_calls": 0,
            "no_answer_calls": 0,
            "error_calls": 0
        }
        logger.info("Estadísticas reiniciadas")

# Instancia global del gestor (singleton)
_call_manager = None

def get_call_manager() -> CallManager:
    """
    Obtiene una instancia singleton del gestor de llamadas.
    
    Returns:
        CallManager: Instancia del gestor de llamadas
    """
    global _call_manager
    if _call_manager is None:
        from flask import current_app
        _call_manager = CallManager(
            app=current_app,
            pearl_client=get_pearl_client(),
            on_status_update=None
        )
    return _call_manager

if __name__ == "__main__":
    # Código de prueba
    print("🧪 Probando gestor de llamadas...")
    
    try:
        manager = get_call_manager()
        print(f"✅ Gestor inicializado")
        
        # Mostrar estado
        status = manager.get_status()
        print(f"📊 Estado: {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

"""
Gestor de cola y estado de llamadas automáticas.
Maneja la lógica de negocio para procesar leads, gestionar la cola de llamadas
y coordinar con la API de Pearl AI.
"""

import threading
import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from queue import Queue, Empty
from dataclasses import dataclass
from enum import Enum

from db import get_connection
from pearl_caller import get_pearl_client, PearlAPIError

# Configurar logging
logger = logging.getLogger(__name__)

# Teléfono de prueba opcional (override). Puede establecerse vía variable de entorno TEST_CALL_PHONE
_override_phone = os.getenv("TEST_CALL_PHONE")

def set_override_phone(phone: str | None):
    """Permite establecer o limpiar el número de teléfono de override."""
    global _override_phone
    _override_phone = phone.strip() if phone else None
    if _override_phone:
        logger.warning(f"☎️  Modo prueba activado: todas las llamadas se dirigirán a {_override_phone}")
    else:
        logger.info("Modo prueba desactivado: se usará el teléfono de cada lead")

class CallStatus(Enum):
    """Estados posibles de una llamada."""
    NO_SELECTED = "no_selected"
    SELECTED = "selected"
    CALLING = "calling"
    COMPLETED = "completed"
    ERROR = "error"
    BUSY = "busy"
    NO_ANSWER = "no_answer"

@dataclass
class CallTask:
    """Representa una tarea de llamada en la cola."""
    lead_id: int
    phone_number: str
    lead_data: Dict
    priority: int
    outbound_id: str
    attempts: int = 0
    max_attempts: int = 3

class CallManager:
    """Gestor principal de llamadas automáticas."""
    
    def __init__(self, max_concurrent_calls: int = 3):
        """
        Inicializa el gestor de llamadas.
        
        Args:
            max_concurrent_calls (int): Número máximo de llamadas simultáneas
        """
        self.max_concurrent_calls = max_concurrent_calls
        self.call_queue = Queue()
        self.active_calls = {}  # {lead_id: thread}
        self.is_running = False
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "busy_calls": 0,
            "no_answer_calls": 0,
            "error_calls": 0
        }
        
        # Callbacks para eventos
        self.on_call_started = None
        self.on_call_completed = None
        self.on_call_failed = None
        self.on_stats_updated = None
        
        # Thread principal del gestor
        self.manager_thread = None
        self.stop_event = threading.Event()
        
        # Pearl AI client
        self.pearl_client = get_pearl_client()
        
        logger.info(f"CallManager inicializado con {max_concurrent_calls} llamadas simultáneas")
    
    def set_callbacks(self, 
                     on_call_started: Optional[Callable] = None,
                     on_call_completed: Optional[Callable] = None,
                     on_call_failed: Optional[Callable] = None,
                     on_stats_updated: Optional[Callable] = None):
        """Configura callbacks para eventos del gestor."""
        self.on_call_started = on_call_started
        self.on_call_completed = on_call_completed
        self.on_call_failed = on_call_failed
        self.on_stats_updated = on_stats_updated
    
    def start_calling(self) -> bool:
        """
        Inicia el proceso de llamadas automáticas.
        
        Returns:
            bool: True si se inició correctamente, False en caso contrario
        """
        if self.is_running:
            logger.warning("El gestor de llamadas ya está ejecutándose")
            return False
        
        try:
            # Probar conexión con Pearl AI
            if not self.pearl_client.test_connection():
                logger.error("No se puede conectar con Pearl AI")
                return False
            
            # Cargar leads seleccionados
            selected_leads = self._load_selected_leads()
            if not selected_leads:
                logger.warning("No hay leads seleccionados para llamar")
                return False
            
            # Añadir leads a la cola
            for lead in selected_leads:
                self._add_lead_to_queue(lead)
            
            # Iniciar el gestor
            self.is_running = True
            self.stop_event.clear()
            self.manager_thread = threading.Thread(target=self._run_manager, daemon=True)
            self.manager_thread.start()
            
            logger.info(f"✅ Gestor de llamadas iniciado con {len(selected_leads)} leads en cola")
            return True
            
        except Exception as e:
            logger.error(f"Error al iniciar gestor de llamadas: {e}")
            return False
    
    def stop_calling(self) -> bool:
        """
        Detiene el proceso de llamadas automáticas.
        
        Returns:
            bool: True si se detuvo correctamente, False en caso contrario
        """
        if not self.is_running:
            logger.warning("El gestor de llamadas no está ejecutándose")
            return False
        
        try:
            logger.info("Deteniendo gestor de llamadas...")
            self.is_running = False
            self.stop_event.set()
            
            # Esperar a que termine el thread principal
            if self.manager_thread and self.manager_thread.is_alive():
                self.manager_thread.join(timeout=10)
            
            # Actualizar estado de leads que estaban siendo llamados
            self._cleanup_active_calls()
            
            logger.info("✅ Gestor de llamadas detenido")
            return True
            
        except Exception as e:
            logger.error(f"Error al detener gestor de llamadas: {e}")
            return False
    
    def get_status(self) -> Dict:
        """
        Obtiene el estado actual del gestor de llamadas.
        
        Returns:
            Dict: Estado actual con estadísticas e información
        """
        return {
            "is_running": self.is_running,
            "queue_size": self.call_queue.qsize(),
            "active_calls": len(self.active_calls),
            "max_concurrent": self.max_concurrent_calls,
            "stats": self.stats.copy()
        }
    
    def add_leads_to_queue(self, lead_ids: List[int]) -> int:
        """
        Añade leads específicos a la cola de llamadas.
        
        Args:
            lead_ids (List[int]): Lista de IDs de leads a añadir
            
        Returns:
            int: Número de leads añadidos exitosamente
        """
        added_count = 0
        
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Obtener leads válidos
            placeholders = ','.join(['%s'] * len(lead_ids))
            query = f"""
                SELECT id, nombre, apellidos, telefono, ciudad, nombre_clinica,
                       call_priority, pearl_outbound_id
                FROM leads 
                WHERE id IN ({placeholders})
                AND telefono IS NOT NULL 
                AND telefono != ''
                AND call_status != 'calling'
            """
            
            cursor.execute(query, lead_ids)
            leads = cursor.fetchall()
            
            for lead in leads:
                if self._add_lead_to_queue(lead):
                    added_count += 1
            
            logger.info(f"Añadidos {added_count} leads a la cola de llamadas")
            
        except Exception as e:
            logger.error(f"Error al añadir leads a la cola: {e}")
        finally:
            if conn:
                conn.close()
        
        return added_count
    
    def _load_selected_leads(self) -> List[Dict]:
        """
        Carga leads seleccionados para llamar desde la base de datos.
        
        Returns:
            List[Dict]: Lista de leads seleccionados
        """
        leads = []
        
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id, nombre, apellidos, telefono, telefono2, ciudad, 
                    nombre_clinica, call_priority, pearl_outbound_id,
                    call_attempts_count, nif, fecha_nacimiento, sexo, email, 
                    poliza, segmento, certificado, delegacion, clinica_id, 
                    direccion_clinica, codigo_postal, orden
                FROM leads 
                WHERE selected_for_calling = TRUE
                AND telefono IS NOT NULL
                AND telefono != ''
                AND call_status IN ('no_selected', 'selected', 'error')
                ORDER BY call_priority ASC, id ASC
            """
            
            cursor.execute(query)
            leads = cursor.fetchall()
            
            logger.info(f"Cargados {len(leads)} leads seleccionados para llamar")
            
        except Exception as e:
            logger.error(f"Error al cargar leads seleccionados: {e}")
        finally:
            if conn:
                conn.close()
        
        return leads
    
    def _add_lead_to_queue(self, lead_data: Dict) -> bool:
        """
        Añade un lead a la cola de llamadas.
        
        Args:
            lead_data (Dict): Datos del lead
            _override_phone (str): Teléfono de prueba para override
            
        Returns:
            bool: True si se añadió correctamente
        """
        try:
            # Obtener el teléfono (override si está configurado)
            phone = _override_phone if _override_phone else lead_data.get('telefono', '').strip()
            if not self.pearl_client.validate_phone_number(phone):
                # Intentar con teléfono secundario
                phone = _override_phone if _override_phone else lead_data.get('telefono2', '').strip()
                if not self.pearl_client.validate_phone_number(phone):
                    logger.warning(f"Lead {lead_data['id']}: números de teléfono inválidos")
                    self._update_lead_status(lead_data['id'], CallStatus.ERROR, 
                                           "Número de teléfono inválido")
                    return False
            
            # Formatear número
            formatted_phone = self.pearl_client.format_phone_number(phone)
            
            # Determinar outbound ID
            outbound_id = (lead_data.get('pearl_outbound_id') or 
                          self.pearl_client.get_default_outbound_id())
            
            if not outbound_id:
                logger.error(f"Lead {lead_data['id']}: No hay outbound ID configurado")
                self._update_lead_status(lead_data['id'], CallStatus.ERROR, 
                                       "No hay outbound ID configurado")
                return False
            
            # Crear tarea de llamada
            task = CallTask(
                lead_id=lead_data['id'],
                phone_number=formatted_phone,
                lead_data=lead_data,
                priority=lead_data.get('call_priority', 3),
                outbound_id=outbound_id,
                attempts=lead_data.get('call_attempts_count', 0)
            )
            
            # Añadir a la cola
            self.call_queue.put(task)
            
            # Actualizar estado a 'selected'
            self._update_lead_status(lead_data['id'], CallStatus.SELECTED)
            
            return True
            
        except Exception as e:
            logger.error(f"Error al añadir lead {lead_data.get('id', 'N/A')} a la cola: {e}")
            return False
    
    def _run_manager(self):
        """
        Hilo principal del gestor de llamadas.
        Procesa la cola y gestiona llamadas concurrentes.
        """
        logger.info("🚀 Iniciando hilo principal del gestor de llamadas")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Procesar llamadas completadas
                self._cleanup_completed_calls()
                
                # Verificar si podemos hacer más llamadas
                if len(self.active_calls) >= self.max_concurrent_calls:
                    time.sleep(1)
                    continue
                
                # Obtener siguiente tarea de la cola
                try:
                    task = self.call_queue.get(timeout=1)
                except Empty:
                    # Si no hay tareas, verificar si terminamos
                    if len(self.active_calls) == 0:
                        logger.info("Cola vacía y no hay llamadas activas. Terminando...")
                        break
                    continue
                
                # Iniciar llamada
                self._start_call(task)
                
            except Exception as e:
                logger.error(f"Error en hilo principal del gestor: {e}")
                time.sleep(1)
        
        # Limpiar al terminar
        self._cleanup_active_calls()
        self.is_running = False
        logger.info("🏁 Hilo principal del gestor terminado")
    
    def _start_call(self, task: CallTask):
        """
        Inicia una llamada individual en un hilo separado.
        
        Args:
            task (CallTask): Tarea de llamada a ejecutar
        """
        try:
            # Actualizar estado a 'calling'
            self._update_lead_status(task.lead_id, CallStatus.CALLING)
            
            # Crear y iniciar hilo de llamada
            call_thread = threading.Thread(
                target=self._execute_call, 
                args=(task,), 
                daemon=True
            )
            
            self.active_calls[task.lead_id] = {
                'thread': call_thread,
                'task': task,
                'started_at': datetime.now()
            }
            
            call_thread.start()
            
            # Callback de inicio
            if self.on_call_started:
                try:
                    self.on_call_started(task.lead_id, task.phone_number)
                except Exception as e:
                    logger.error(f"Error en callback on_call_started: {e}")
            
            logger.info(f"📞 Iniciada llamada a lead {task.lead_id}: {task.phone_number}")
            
        except Exception as e:
            logger.error(f"Error al iniciar llamada para lead {task.lead_id}: {e}")
            self._update_lead_status(task.lead_id, CallStatus.ERROR, str(e))
    
    def _execute_call(self, task: CallTask):
        """
        Ejecuta una llamada individual.
        
        Args:
            task (CallTask): Tarea de llamada
        """
        success = False
        error_message = None
        
        try:
            # Realizar la llamada
            success, response = self.pearl_client.make_call(
                task.outbound_id,
                task.phone_number,
                task.lead_data
            )
            
            # Actualizar estadísticas
            self.stats["total_calls"] += 1
            
            if success:
                self.stats["successful_calls"] += 1
                status = CallStatus.COMPLETED
                
                # Guardar respuesta de Pearl AI
                self._update_lead_call_data(task.lead_id, response)
                
                logger.info(f"✅ Llamada exitosa - Lead {task.lead_id}")
                
                # Callback de éxito
                if self.on_call_completed:
                    try:
                        self.on_call_completed(task.lead_id, task.phone_number, response)
                    except Exception as e:
                        logger.error(f"Error en callback on_call_completed: {e}")
            else:
                # Analizar tipo de error
                error_message = response.get('error', 'Error desconocido')
                
                if 'busy' in error_message.lower():
                    status = CallStatus.BUSY
                    self.stats["busy_calls"] += 1
                elif 'no answer' in error_message.lower():
                    status = CallStatus.NO_ANSWER
                    self.stats["no_answer_calls"] += 1
                else:
                    status = CallStatus.ERROR
                    self.stats["error_calls"] += 1
                
                self.stats["failed_calls"] += 1
                
                logger.warning(f"⚠️ Llamada fallida - Lead {task.lead_id}: {error_message}")
                
                # Callback de fallo
                if self.on_call_failed:
                    try:
                        self.on_call_failed(task.lead_id, task.phone_number, error_message)
                    except Exception as e:
                        logger.error(f"Error en callback on_call_failed: {e}")
        
        except Exception as e:
            error_message = f"Excepción durante llamada: {str(e)}"
            status = CallStatus.ERROR
            self.stats["error_calls"] += 1
            self.stats["failed_calls"] += 1
            logger.error(f"❌ Error ejecutando llamada - Lead {task.lead_id}: {e}")
        
        finally:
            # Actualizar estado del lead
            self._update_lead_status(task.lead_id, status, error_message)
            
            # Incrementar contador de intentos
            self._increment_call_attempts(task.lead_id)
            
            # Callback de estadísticas
            if self.on_stats_updated:
                try:
                    self.on_stats_updated(self.stats.copy())
                except Exception as e:
                    logger.error(f"Error en callback on_stats_updated: {e}")
    
    def _update_lead_status(self, lead_id: int, status: CallStatus, error_message: str = None):
        """
        Actualiza el estado de un lead en la base de datos.
        
        Args:
            lead_id (int): ID del lead
            status (CallStatus): Nuevo estado
            error_message (str, optional): Mensaje de error si aplica
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            update_fields = [
                "call_status = %s",
                "last_call_attempt = %s",
                "updated_at = CURRENT_TIMESTAMP"
            ]
            values = [status.value, datetime.now()]
            
            if error_message:
                update_fields.append("call_error_message = %s")
                values.append(error_message)
            
            query = f"UPDATE leads SET {', '.join(update_fields)} WHERE id = %s"
            values.append(lead_id)
            
            cursor.execute(query, values)
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error actualizando estado de lead {lead_id}: {e}")
        finally:
            if conn:
                conn.close()
    
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
        CallManager: Gestor configurado
    """
    global _call_manager
    if _call_manager is None:
        _call_manager = CallManager()
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

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
from models import Lead, Call, Session, db
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


class CallStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"


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
        phone = _override_phone if _override_phone else lead_data.get('telefono', '').strip()
        if not self.pearl_client.validate_phone_number(phone):
            phone = _override_phone if _override_phone else lead_data.get('telefono2', '').strip()

        if self.pearl_client.validate_phone_number(phone):
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
            with self.app.app_context():
                lead = Lead.query.get(lead_id)
                if lead:
                    lead.call_status = status
                    lead.last_call_time = datetime.utcnow()
                    lead.call_attempts = (lead.call_attempts or 0) + 1
                    if error_message:
                        lead.last_call_error = error_message
                    db.session.commit()
                    if self.on_status_update:
                        self.on_status_update('lead_update', lead.to_dict())
        except Exception as e:
            logger.error(f"Error actualizando estado de lead {lead_id}: {e}")

    def _create_call_record(self, lead_id: int, phone_number: str) -> int:
        with self.app.app_context():
            new_call = Call(
                lead_id=lead_id,
                session_id=self.current_session_id,
                phone_number=phone_number,
                status='initiated'
            )
            db.session.add(new_call)
            db.session.commit()
            return new_call.id

    def _update_call_record(self, call_id: int, status: str, duration: Optional[int] = None, error_message: Optional[str] = None):
        with self.app.app_context():
            call = Call.query.get(call_id)
            if call:
                call.status = status
                call.end_time = datetime.utcnow()
                if duration is not None:
                    call.duration_seconds = duration
                if error_message:
                    call.error_message = error_message
                db.session.commit()

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

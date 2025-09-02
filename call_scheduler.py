"""
Sistema de Scheduler Automático para Llamadas
Gestiona la reprogramación automática de llamadas según los resultados.

Funcionalidades:
- Reprogramar llamadas fallidas después de 30 horas
- Respetar horarios laborables (10AM-8PM, parametrizable)
- Máximo 6 intentos antes de cerrar automáticamente
- Cierre automático con razones específicas
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from db import get_connection
import logging
import json
from typing import Dict, List, Optional, Tuple

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CallScheduler:
    def __init__(self):
        self.config = {}
        self.load_config()
    
    def load_config(self) -> Dict:
        """Carga la configuración desde la base de datos."""
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD para cargar configuración")
            return
        
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT config_key, config_value FROM scheduler_config")
                configs = cursor.fetchall()
                
                for config in configs:
                    key = config['config_key']
                    value = config['config_value']
                    
                    # Parsear valores JSON
                    if key in ['closure_reasons', 'working_days']:
                        self.config[key] = json.loads(value)
                    else:
                        self.config[key] = value
                        
                logger.info(f"Configuracion cargada: {len(self.config)} parametros")
                
        except Error as e:
            logger.error(f"Error cargando configuracion: {e}")
        finally:
            conn.close()
    
    def get_working_hours(self) -> Tuple[str, str]:
        """Obtiene las horas laborables."""
        start = self.config.get('working_hours_start', '10:00')
        end = self.config.get('working_hours_end', '20:00')
        return start, end
    
    def is_working_time(self, dt: datetime) -> bool:
        """Verifica si una fecha/hora está en horario laboral."""
        # Verificar día de la semana (1=Lunes, 7=Domingo)
        working_days = self.config.get('working_days', [1, 2, 3, 4, 5])
        weekday = dt.isoweekday()  # 1=Monday, 7=Sunday
        
        if weekday not in working_days:
            return False
        
        # Verificar hora
        start_hour, end_hour = self.get_working_hours()
        current_time = dt.time()
        
        # Convertir strings de hora a time objects
        from datetime import time
        start_time = time(*map(int, start_hour.split(':')))
        end_time = time(*map(int, end_hour.split(':')))
        
        return start_time <= current_time <= end_time
    
    def find_next_working_slot(self, base_datetime: datetime) -> datetime:
        """Encuentra el siguiente slot en horario laboral."""
        candidate = base_datetime
        working_days = self.config.get('working_days', [1, 2, 3, 4, 5])
        start_hour, _ = self.get_working_hours()
        
        # Si ya está en horario laboral, devolverlo
        if self.is_working_time(candidate):
            return candidate
        
        # Buscar el siguiente día/hora laboral
        max_iterations = 14  # Máximo 2 semanas
        iterations = 0
        
        while not self.is_working_time(candidate) and iterations < max_iterations:
            iterations += 1
            weekday = candidate.isoweekday()
            
            if weekday in working_days:
                # Es día laboral, ajustar solo la hora
                start_time = datetime.strptime(start_hour, '%H:%M').time()
                candidate = candidate.replace(
                    hour=start_time.hour, 
                    minute=start_time.minute, 
                    second=0, 
                    microsecond=0
                )
                if self.is_working_time(candidate):
                    break
            
            # Pasar al siguiente día a la hora de inicio
            candidate = candidate.replace(
                hour=int(start_hour.split(':')[0]), 
                minute=int(start_hour.split(':')[1]), 
                second=0, 
                microsecond=0
            ) + timedelta(days=1)
        
        return candidate
    
    def schedule_retry(self, lead_id: int, outcome: str) -> bool:
        """
        Programa un reintento para un lead según el resultado.
        
        Args:
            lead_id: ID del lead
            outcome: Resultado de la llamada ('no_answer', 'busy', 'hang_up', etc.)
        
        Returns:
            bool: True si se programó correctamente, False si se cerró el lead
        """
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD")
            return False
        
        try:
            with conn.cursor(dictionary=True) as cursor:
                # Obtener información actual del lead
                cursor.execute("""
                    SELECT id, call_attempts_count, lead_status, telefono, nombre, apellidos
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
                
                # Incrementar contador de intentos
                attempts = (lead['call_attempts_count'] or 0) + 1
                max_attempts = int(self.config.get('max_attempts', 6))
                
                # Si alcanzó el máximo de intentos, cerrar el lead
                if attempts >= max_attempts:
                    return self._close_lead(cursor, lead_id, outcome, attempts)
                
                # Calcular fecha de reprogramación (30 horas después)
                reschedule_hours = int(self.config.get('reschedule_hours', 30))
                next_attempt_time = datetime.now() + timedelta(hours=reschedule_hours)
                
                # Ajustar al siguiente horario laboral
                scheduled_time = self.find_next_working_slot(next_attempt_time)
                
                # Actualizar el lead
                cursor.execute("""
                    UPDATE leads SET
                        call_attempts_count = %s,
                        last_call_attempt = NOW(),
                        call_status = 'selected',
                        updated_at = NOW()
                    WHERE id = %s
                """, (attempts, lead_id))
                
                # Insertar en call_schedule
                cursor.execute("""
                    INSERT INTO call_schedule 
                    (lead_id, scheduled_at, attempt_number, status, last_outcome)
                    VALUES (%s, %s, %s, 'pending', %s)
                """, (lead_id, scheduled_time, attempts, outcome))
                
                conn.commit()
                
                logger.info(f"Lead {lead_id} ({lead['nombre']} {lead['apellidos']}) "
                           f"reprogramado para {scheduled_time} (intento {attempts}/{max_attempts})")
                
                return True
                
        except Error as e:
            logger.error(f"Error programando reintento para lead {lead_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            conn.close()
    
    def _close_lead(self, cursor, lead_id: int, outcome: str, attempts: int) -> bool:
        """Cierra un lead después del máximo de intentos."""
        closure_reasons = self.config.get('closure_reasons', {})
        
        # Determinar razón de cierre según el outcome
        if outcome == 'no_answer':
            closure_reason = closure_reasons.get('no_answer', 'Ilocalizable')
        elif outcome == 'hang_up':
            closure_reason = closure_reasons.get('hang_up', 'No colabora')
        elif outcome in ['invalid_phone', 'error']:
            closure_reason = closure_reasons.get('invalid_phone', 'Telefono erroneo')
        else:
            closure_reason = 'Ilocalizable'  # Por defecto
        
        # Actualizar el lead como cerrado
        cursor.execute("""
            UPDATE leads SET
                lead_status = 'closed',
                closure_reason = %s,
                call_attempts_count = %s,
                call_status = 'completed',
                last_call_attempt = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (closure_reason, attempts, lead_id))
        
        # Cancelar llamadas pendientes en call_schedule
        cursor.execute("""
            UPDATE call_schedule SET
                status = 'cancelled',
                updated_at = NOW()
            WHERE lead_id = %s AND status = 'pending'
        """, (lead_id,))
        
        logger.info(f"Lead {lead_id} CERRADO después de {attempts} intentos. "
                   f"Razón: {closure_reason}")
        
        return False
    
    def get_pending_calls(self, limit: int = 50) -> List[Dict]:
        """Obtiene las llamadas pendientes que deben realizarse ahora."""
        conn = get_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT 
                        cs.id as schedule_id,
                        cs.lead_id,
                        cs.scheduled_at,
                        cs.attempt_number,
                        l.nombre,
                        l.apellidos,
                        l.telefono,
                        l.call_attempts_count,
                        l.lead_status
                    FROM call_schedule cs
                    JOIN leads l ON cs.lead_id = l.id
                    WHERE cs.status = 'pending'
                        AND cs.scheduled_at <= NOW()
                        AND l.lead_status = 'open'
                        AND (l.manual_management IS NULL OR l.manual_management = FALSE)
                    ORDER BY cs.scheduled_at ASC, cs.attempt_number ASC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
                
        except Error as e:
            logger.error(f"Error obteniendo llamadas pendientes: {e}")
            return []
        finally:
            conn.close()
    
    def mark_call_completed(self, schedule_id: int, success: bool = True) -> bool:
        """Marca una llamada programada como completada."""
        conn = get_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                status = 'completed' if success else 'failed'
                cursor.execute("""
                    UPDATE call_schedule 
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                """, (status, schedule_id))
                
                conn.commit()
                return True
                
        except Error as e:
            logger.error(f"Error marcando llamada {schedule_id} como completada: {e}")
            return False
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas del scheduler."""
        conn = get_connection()
        if not conn:
            return {}
        
        try:
            with conn.cursor(dictionary=True) as cursor:
                stats = {}
                
                # Llamadas pendientes
                cursor.execute("""
                    SELECT COUNT(*) as count FROM call_schedule 
                    WHERE status = 'pending' AND scheduled_at <= NOW()
                """)
                stats['pending_calls'] = cursor.fetchone()['count']
                
                # Llamadas programadas para hoy
                cursor.execute("""
                    SELECT COUNT(*) as count FROM call_schedule 
                    WHERE status = 'pending' 
                        AND DATE(scheduled_at) = CURDATE()
                """)
                stats['scheduled_today'] = cursor.fetchone()['count']
                
                # Leads cerrados por el scheduler
                cursor.execute("""
                    SELECT 
                        closure_reason,
                        COUNT(*) as count
                    FROM leads 
                    WHERE lead_status = 'closed' 
                        AND closure_reason IS NOT NULL
                    GROUP BY closure_reason
                """)
                closure_stats = cursor.fetchall()
                stats['closures'] = {row['closure_reason']: row['count'] for row in closure_stats}
                
                # Estadísticas de intentos
                cursor.execute("""
                    SELECT 
                        AVG(call_attempts_count) as avg_attempts,
                        MAX(call_attempts_count) as max_attempts
                    FROM leads 
                    WHERE call_attempts_count > 0
                """)
                attempt_stats = cursor.fetchone()
                stats['avg_attempts'] = float(attempt_stats['avg_attempts'] or 0)
                stats['max_attempts'] = int(attempt_stats['max_attempts'] or 0)
                
                return stats
                
        except Error as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
        finally:
            conn.close()

# Funciones de utilidad para integración con el sistema actual
def schedule_failed_call(lead_id: int, outcome: str) -> bool:
    """Función de conveniencia para programar una llamada fallida."""
    scheduler = CallScheduler()
    return scheduler.schedule_retry(lead_id, outcome)

def get_next_scheduled_calls(limit: int = 10) -> List[Dict]:
    """Función de conveniencia para obtener próximas llamadas."""
    scheduler = CallScheduler()
    return scheduler.get_pending_calls(limit)

if __name__ == "__main__":
    # Prueba del sistema
    print("Probando sistema de scheduler...")
    
    scheduler = CallScheduler()
    
    # Mostrar configuración
    print(f"Configuracion cargada: {scheduler.config}")
    
    # Mostrar estadísticas
    stats = scheduler.get_statistics()
    print(f"Estadisticas: {stats}")
    
    # Mostrar llamadas pendientes
    pending = scheduler.get_pending_calls(5)
    print(f"Llamadas pendientes: {len(pending)}")
    for call in pending:
        print(f"  - Lead {call['lead_id']}: {call['nombre']} {call['apellidos']} "
              f"programado para {call['scheduled_at']} (intento {call['attempt_number']})")
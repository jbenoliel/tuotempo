"""
CallScheduler mejorado con soporte para múltiples franjas horarias.

Formato de configuración:
- working_time_slots: [{"start": "12:00", "end": "14:00"}, {"start": "18:00", "end": "21:00"}]
- Mantiene compatibilidad con formato anterior (working_hours_start/end)

Ejemplos de uso:
1. Horario continuo: [{"start": "09:00", "end": "18:00"}]
2. Con descanso almuerzo: [{"start": "09:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}]
3. Turnos noche: [{"start": "22:00", "end": "23:59"}, {"start": "00:00", "end": "06:00"}]
4. Tu ejemplo: [{"start": "12:00", "end": "14:00"}, {"start": "18:00", "end": "21:00"}]
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta, time
import logging
from db import get_connection
import json
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class CallSchedulerMultiTimeframes:
    def __init__(self):
        # Initialize with safe defaults
        self.config = {
            'max_attempts': 6,
            'reschedule_hours': 30,
            'working_time_slots': [{"start": "10:00", "end": "20:00"}],  # Default single slot
            'working_days': [1, 2, 3, 4, 5],
            'closure_reasons': {}
        }
        self._config_loaded = False

    def _ensure_config_loaded(self):
        """Carga la configuración si no se ha cargado aún (lazy loading)."""
        if not self._config_loaded:
            try:
                self.load_config()
            except Exception as e:
                logger.warning(f"Could not load config from database, using defaults: {e}")
            self._config_loaded = True

    def load_config(self) -> Dict:
        """Carga la configuración desde la base de datos con soporte para múltiples formatos."""
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD para cargar configuración")
            return

        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT config_key, config_value FROM scheduler_config")
                configs = cursor.fetchall()

                has_time_slots = False
                legacy_start = None
                legacy_end = None

                for config in configs:
                    if config is None:
                        continue

                    key = config.get('config_key')
                    value = config.get('config_value')

                    # Handle bytearray values
                    if isinstance(key, bytearray):
                        key = key.decode('utf-8')
                    if isinstance(value, bytearray):
                        value = value.decode('utf-8')

                    key = str(key) if key is not None else None
                    value = str(value) if value is not None else None

                    if key is None or value is None:
                        continue

                    # Manejar nueva configuración de time_slots
                    if key == 'working_time_slots':
                        try:
                            self.config[key] = json.loads(value)
                            has_time_slots = True
                            logger.info(f"Cargadas {len(self.config[key])} franjas horarias")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(f"Error parsing working_time_slots: {e}")
                            # Mantener default

                    # Mantener compatibilidad con formato anterior
                    elif key == 'working_hours_start':
                        legacy_start = value
                    elif key == 'working_hours_end':
                        legacy_end = value

                    # Otras configuraciones
                    elif key in ['closure_reasons', 'working_days']:
                        try:
                            self.config[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            if key == 'working_days':
                                self.config[key] = [1, 2, 3, 4, 5]
                            elif key == 'closure_reasons':
                                self.config[key] = {}
                    else:
                        self.config[key] = value

                # Si no hay working_time_slots pero hay formato legacy, convertir
                if not has_time_slots and legacy_start and legacy_end:
                    self.config['working_time_slots'] = [
                        {"start": legacy_start, "end": legacy_end}
                    ]
                    logger.info(f"Convertido formato legacy a time_slots: {legacy_start}-{legacy_end}")

                logger.info(f"Configuración cargada: {len(self.config)} parámetros")

        except Error as e:
            logger.error(f"Error cargando configuración: {e}")
            # Mantener defaults si falla la carga
        except Exception as e:
            logger.error(f"Error inesperado cargando configuración: {e}")
        finally:
            if conn:
                conn.close()

    def get_working_time_slots(self) -> List[Dict[str, str]]:
        """Obtiene las franjas horarias de trabajo."""
        self._ensure_config_loaded()
        slots = self.config.get('working_time_slots', [{"start": "10:00", "end": "20:00"}])

        # Validar formato de slots
        validated_slots = []
        for slot in slots:
            if isinstance(slot, dict) and 'start' in slot and 'end' in slot:
                start = str(slot['start'])
                end = str(slot['end'])

                # Validar formato HH:MM
                if ':' in start and ':' in end:
                    try:
                        # Verificar que se pueden convertir a time objects
                        time(*map(int, start.split(':')))
                        time(*map(int, end.split(':')))
                        validated_slots.append({"start": start, "end": end})
                    except (ValueError, TypeError):
                        logger.warning(f"Slot inválido ignorado: {slot}")

        # Si no hay slots válidos, usar default
        if not validated_slots:
            validated_slots = [{"start": "10:00", "end": "20:00"}]

        return validated_slots

    def get_working_hours(self) -> Tuple[str, str]:
        """Compat: devuelve (inicio, fin) agregados de las franjas laborales.

        - Toma la hora de inicio más temprana y la hora de fin más tardía
          entre todos los `working_time_slots` válidos.
        - Si no hay franjas válidas, usa defaults seguros '10:00'-'20:00'.
        - Mantiene compatibilidad con consumidores que esperan un par (start, end).
        """
        self._ensure_config_loaded()
        slots = self.get_working_time_slots()

        try:
            # Extraer horas de inicio y fin como tuplas (HH, MM) para poder comparar
            starts = []
            ends = []
            for slot in slots:
                s = str(slot.get('start', '10:00'))
                e = str(slot.get('end', '20:00'))
                if ':' in s and ':' in e:
                    s_h, s_m = map(int, s.split(':')[:2])
                    e_h, e_m = map(int, e.split(':')[:2])
                    starts.append((s_h, s_m, s))
                    ends.append((e_h, e_m, e))

            if not starts or not ends:
                return '10:00', '20:00'

            # Elegir el inicio más temprano y el fin más tardío
            earliest_start = min(starts)  # compara por (h, m)
            latest_end = max(ends)
            return earliest_start[2], latest_end[2]
        except Exception:
            # Fallback seguro
            return '10:00', '20:00'

    def is_working_time(self, dt: datetime) -> bool:
        """Verifica si una fecha/hora está en alguna de las franjas laborales."""
        self._ensure_config_loaded()

        # Verificar día de la semana
        working_days = self.config.get('working_days', [1, 2, 3, 4, 5])
        weekday = dt.isoweekday()  # 1=Monday, 7=Sunday

        if weekday not in working_days:
            return False

        # Verificar si está en alguna franja horaria
        current_time = dt.time()
        time_slots = self.get_working_time_slots()

        for slot in time_slots:
            start_time = time(*map(int, slot['start'].split(':')))
            end_time = time(*map(int, slot['end'].split(':')))

            # Manejar franjas que cruzan medianoche (ej: 22:00-06:00)
            if start_time <= end_time:
                # Franja normal (ej: 09:00-17:00)
                if start_time <= current_time <= end_time:
                    return True
            else:
                # Franja que cruza medianoche (ej: 22:00-06:00)
                if current_time >= start_time or current_time <= end_time:
                    return True

        return False

    def find_next_working_slot(self, base_datetime: datetime) -> datetime:
        """Encuentra el siguiente slot en horario laboral considerando múltiples franjas."""
        self._ensure_config_loaded()

        if self.is_working_time(base_datetime):
            return base_datetime

        candidate = base_datetime
        working_days = self.config.get('working_days', [1, 2, 3, 4, 5])
        time_slots = self.get_working_time_slots()

        # Buscar hasta 14 días en el futuro
        for day_offset in range(14):
            test_date = (candidate + timedelta(days=day_offset)).date()
            test_weekday = test_date.isoweekday()

            if test_weekday in working_days:
                # Buscar la primera franja disponible en este día
                for slot in time_slots:
                    slot_start_time = time(*map(int, slot['start'].split(':')))
                    slot_datetime = datetime.combine(test_date, slot_start_time)

                    # Si es el mismo día, debe ser posterior a la hora base
                    if day_offset == 0 and slot_datetime <= candidate:
                        continue

                    if self.is_working_time(slot_datetime):
                        return slot_datetime

        # Fallback: usar primera franja del primer día laboral
        return candidate + timedelta(days=1)

    def get_current_working_slot_info(self, dt: datetime) -> Optional[Dict[str, str]]:
        """Obtiene información de la franja actual si está en horario laboral."""
        if not self.is_working_time(dt):
            return None

        current_time = dt.time()
        time_slots = self.get_working_time_slots()

        for slot in time_slots:
            start_time = time(*map(int, slot['start'].split(':')))
            end_time = time(*map(int, slot['end'].split(':')))

            if start_time <= end_time:
                if start_time <= current_time <= end_time:
                    return slot
            else:
                if current_time >= start_time or current_time <= end_time:
                    return slot

        return None

    def schedule_retry(self, lead_id: int, outcome: str) -> bool:
        """Programa un reintento considerando múltiples franjas horarias."""
        if outcome is None:
            outcome = 'unknown'
        if not isinstance(outcome, str):
            outcome = str(outcome) if outcome is not None else 'unknown'

        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD")
            return False

        try:
            with conn.cursor(dictionary=True) as cursor:
                # Obtener información del lead
                cursor.execute("""
                    SELECT id AS real_id, call_attempts_count, lead_status, telefono, nombre, apellidos
                    FROM leads
                    WHERE id = %s
                """, (lead_id,))
                lead = cursor.fetchone()

                if not lead:
                    logger.error(f"Lead {lead_id} no existe en la BD")
                    return False

                lead_id = lead['real_id']

                if lead['lead_status'] == 'closed':
                    logger.info(f"Lead {lead_id} ya está cerrado")
                    return False

                # Incrementar contador e verificar máximo
                attempts = (lead['call_attempts_count'] or 0) + 1
                self._ensure_config_loaded()
                max_attempts = int(self.config.get('max_attempts', 6) or 6)

                if attempts >= max_attempts:
                    return self._close_lead(cursor, lead_id, outcome, attempts)

                # Calcular próxima fecha considerando múltiples franjas
                reschedule_hours = float(self.config.get('reschedule_hours', 30) or 30)
                next_attempt_time = datetime.now() + timedelta(hours=reschedule_hours)
                scheduled_time = self.find_next_working_slot(next_attempt_time)

                # Actualizar lead
                cursor.execute("""
                    UPDATE leads SET
                        call_attempts_count = %s,
                        last_call_attempt = NOW(),
                        call_status = 'selected',
                        updated_at = NOW()
                    WHERE id = %s
                """, (attempts, lead_id))

                # Gestionar call_schedule
                cursor.execute("""
                    SELECT id FROM call_schedule
                    WHERE lead_id = %s AND status = 'pending'
                    LIMIT 1
                """, (lead_id,))

                existing_schedule = cursor.fetchone()

                if existing_schedule:
                    cursor.execute("""
                        UPDATE call_schedule SET
                            scheduled_at = %s,
                            attempt_number = %s,
                            last_outcome = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (scheduled_time, attempts, outcome, existing_schedule['id']))
                else:
                    cursor.execute("""
                        INSERT INTO call_schedule
                        (lead_id, scheduled_at, attempt_number, status, last_outcome)
                        VALUES (%s, %s, %s, 'pending', %s)
                    """, (lead_id, scheduled_time, attempts, outcome))

                conn.commit()

                # Log con información de franja
                slot_info = self.get_current_working_slot_info(scheduled_time)
                slot_desc = f"franja {slot_info['start']}-{slot_info['end']}" if slot_info else "fuera de franjas"

                logger.info(f"Lead {lead_id} ({lead['nombre'] or ''}) reprogramado para "
                           f"{scheduled_time} ({slot_desc}) - intento {attempts}/{max_attempts}")

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
        self._ensure_config_loaded()
        closure_reasons = self.config.get('closure_reasons', {}) or {}

        if outcome == 'no_answer':
            closure_reason = closure_reasons.get('no_answer', 'Ilocalizable')
        elif outcome == 'hang_up':
            closure_reason = closure_reasons.get('hang_up', 'No colabora')
        elif outcome in ['invalid_phone', 'error']:
            closure_reason = closure_reasons.get('invalid_phone', 'Telefono erroneo')
        else:
            closure_reason = 'Ilocalizable'

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

        cursor.execute("""
            UPDATE call_schedule SET
                status = 'cancelled',
                updated_at = NOW()
            WHERE lead_id = %s AND status = 'pending'
        """, (lead_id,))

        logger.info(f"Lead {lead_id} CERRADO después de {attempts} intentos. Razón: {closure_reason}")
        return False

# Mantener compatibilidad con el scheduler anterior
CallScheduler = CallSchedulerMultiTimeframes
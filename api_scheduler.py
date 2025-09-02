"""
API REST para el sistema de Scheduler de llamadas.
Proporciona endpoints para gestionar la programación automática de llamadas.
"""

from flask import Flask, request, jsonify, Blueprint
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List

from db import get_connection
from call_scheduler import CallScheduler, schedule_failed_call, get_next_scheduled_calls

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint para las APIs del scheduler
api_scheduler = Blueprint('api_scheduler', __name__, url_prefix='/api/scheduler')

@api_scheduler.route('/status', methods=['GET'])
def get_scheduler_status():
    """
    Obtiene el estado actual del scheduler.
    
    Returns:
        JSON: Estadísticas y configuración del scheduler
    """
    try:
        scheduler = CallScheduler()
        stats = scheduler.get_statistics()
        
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "configuration": scheduler.config,
            "working_hours": {
                "start": scheduler.config.get('working_hours_start', '10:00'),
                "end": scheduler.config.get('working_hours_end', '20:00'),
                "working_days": scheduler.config.get('working_days', [1,2,3,4,5])
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del scheduler: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_scheduler.route('/schedule', methods=['POST'])
def schedule_call_retry():
    """
    Programa un reintento para un lead específico.
    
    Body JSON:
        {
            "lead_id": 123,
            "outcome": "no_answer|busy|hang_up|error"
        }
    
    Returns:
        JSON: Resultado de la programación
    """
    try:
        data = request.get_json()
        if not data or 'lead_id' not in data or 'outcome' not in data:
            return jsonify({
                "success": False,
                "error": "Faltan parámetros: lead_id y outcome son requeridos"
            }), 400
        
        lead_id = int(data['lead_id'])
        outcome = data['outcome']
        
        # Validar outcome
        valid_outcomes = ['no_answer', 'busy', 'hang_up', 'error', 'invalid_phone']
        if outcome not in valid_outcomes:
            return jsonify({
                "success": False,
                "error": f"Outcome inválido. Debe ser uno de: {', '.join(valid_outcomes)}"
            }), 400
        
        result = schedule_failed_call(lead_id, outcome)
        
        if result:
            return jsonify({
                "success": True,
                "message": f"Lead {lead_id} reprogramado exitosamente",
                "lead_id": lead_id,
                "outcome": outcome,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": True,
                "message": f"Lead {lead_id} cerrado después del máximo de intentos",
                "lead_id": lead_id,
                "outcome": outcome,
                "closed": True,
                "timestamp": datetime.now().isoformat()
            })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"lead_id debe ser un número entero válido"
        }), 400
    except Exception as e:
        logger.error(f"Error programando reintento: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_scheduler.route('/pending', methods=['GET'])
def get_pending_calls():
    """
    Obtiene las llamadas pendientes programadas.
    
    Query parameters:
        - limit: número máximo de resultados (default: 50)
        - due_only: solo llamadas que deben realizarse ahora (default: true)
    
    Returns:
        JSON: Lista de llamadas pendientes
    """
    try:
        limit = int(request.args.get('limit', 50))
        due_only = request.args.get('due_only', 'true').lower() == 'true'
        
        scheduler = CallScheduler()
        
        if due_only:
            calls = scheduler.get_pending_calls(limit)
        else:
            # Obtener todas las llamadas programadas
            conn = get_connection()
            if not conn:
                raise Exception("No se pudo conectar a la base de datos")
            
            try:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute("""
                        SELECT 
                            cs.id as schedule_id,
                            cs.lead_id,
                            cs.scheduled_at,
                            cs.attempt_number,
                            cs.last_outcome,
                            l.nombre,
                            l.apellidos,
                            l.telefono,
                            l.call_attempts_count,
                            l.lead_status
                        FROM call_schedule cs
                        JOIN leads l ON cs.lead_id = l.id
                        WHERE cs.status = 'pending'
                            AND l.lead_status = 'open'
                        ORDER BY cs.scheduled_at ASC
                        LIMIT %s
                    """, (limit,))
                    
                    calls = cursor.fetchall()
            finally:
                conn.close()
        
        # Convertir datetime a string para JSON
        for call in calls:
            if 'scheduled_at' in call and call['scheduled_at']:
                call['scheduled_at'] = call['scheduled_at'].isoformat()
        
        return jsonify({
            "success": True,
            "count": len(calls),
            "calls": calls,
            "due_only": due_only,
            "timestamp": datetime.now().isoformat()
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": "El parámetro 'limit' debe ser un número entero"
        }), 400
    except Exception as e:
        logger.error(f"Error obteniendo llamadas pendientes: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_scheduler.route('/complete/<int:schedule_id>', methods=['POST'])
def mark_call_completed(schedule_id: int):
    """
    Marca una llamada programada como completada.
    
    Body JSON (opcional):
        {
            "success": true|false,
            "outcome": "success|failed",
            "notes": "Notas adicionales"
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json() or {}
        success = data.get('success', True)
        outcome = data.get('outcome', 'success' if success else 'failed')
        notes = data.get('notes', '')
        
        scheduler = CallScheduler()
        result = scheduler.mark_call_completed(schedule_id, success)
        
        if result:
            return jsonify({
                "success": True,
                "message": f"Llamada {schedule_id} marcada como {outcome}",
                "schedule_id": schedule_id,
                "outcome": outcome,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": f"No se pudo marcar la llamada {schedule_id} como completada"
            }), 500
        
    except Exception as e:
        logger.error(f"Error marcando llamada completada: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_scheduler.route('/config', methods=['GET'])
def get_scheduler_config():
    """Obtiene la configuración actual del scheduler."""
    try:
        scheduler = CallScheduler()
        
        return jsonify({
            "success": True,
            "config": scheduler.config,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_scheduler.route('/config', methods=['PUT'])
def update_scheduler_config():
    """
    Actualiza la configuración del scheduler.
    
    Body JSON:
        {
            "working_hours_start": "10:00",
            "working_hours_end": "20:00",
            "reschedule_hours": "30",
            "max_attempts": "6",
            "working_days": [1,2,3,4,5]
        }
    
    Returns:
        JSON: Resultado de la actualización
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No se proporcionaron datos de configuración"
            }), 400
        
        conn = get_connection()
        if not conn:
            raise Exception("No se pudo conectar a la base de datos")
        
        updated_keys = []
        try:
            with conn.cursor() as cursor:
                for key, value in data.items():
                    # Validar claves permitidas
                    allowed_keys = [
                        'working_hours_start', 'working_hours_end', 
                        'reschedule_hours', 'max_attempts', 
                        'working_days', 'closure_reasons'
                    ]
                    
                    if key not in allowed_keys:
                        continue
                    
                    # Convertir listas/dicts a JSON
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    
                    cursor.execute("""
                        UPDATE scheduler_config 
                        SET config_value = %s, updated_at = NOW()
                        WHERE config_key = %s
                    """, (str(value), key))
                    
                    if cursor.rowcount > 0:
                        updated_keys.append(key)
                
                conn.commit()
                
        finally:
            conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Configuración actualizada: {', '.join(updated_keys)}",
            "updated_keys": updated_keys,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error actualizando configuración: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_scheduler.route('/leads/close', methods=['POST'])
def close_leads_manually():
    """
    Cierra leads manualmente con una razón específica.
    
    Body JSON:
        {
            "lead_ids": [1, 2, 3],
            "closure_reason": "Teléfono erróneo|Ilocalizable|No colabora"
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json()
        if not data or 'lead_ids' not in data or 'closure_reason' not in data:
            return jsonify({
                "success": False,
                "error": "Faltan parámetros: lead_ids y closure_reason son requeridos"
            }), 400
        
        lead_ids = data['lead_ids']
        closure_reason = data['closure_reason']
        
        if not isinstance(lead_ids, list) or not lead_ids:
            return jsonify({
                "success": False,
                "error": "lead_ids debe ser una lista no vacía"
            }), 400
        
        # Validar closure_reason
        valid_reasons = ['Teléfono erróneo', 'Ilocalizable', 'No colabora']
        if closure_reason not in valid_reasons:
            return jsonify({
                "success": False,
                "error": f"closure_reason inválido. Debe ser uno de: {', '.join(valid_reasons)}"
            }), 400
        
        conn = get_connection()
        if not conn:
            raise Exception("No se pudo conectar a la base de datos")
        
        closed_count = 0
        try:
            with conn.cursor() as cursor:
                # Cerrar leads
                cursor.execute(f"""
                    UPDATE leads 
                    SET lead_status = 'closed',
                        closure_reason = %s,
                        call_status = 'completed',
                        updated_at = NOW()
                    WHERE id IN ({','.join(['%s'] * len(lead_ids))})
                        AND lead_status = 'open'
                """, [closure_reason] + lead_ids)
                
                closed_count = cursor.rowcount
                
                # Cancelar llamadas pendientes
                cursor.execute(f"""
                    UPDATE call_schedule 
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE lead_id IN ({','.join(['%s'] * len(lead_ids))})
                        AND status = 'pending'
                """, lead_ids)
                
                conn.commit()
                
        finally:
            conn.close()
        
        return jsonify({
            "success": True,
            "message": f"{closed_count} leads cerrados exitosamente",
            "closed_count": closed_count,
            "closure_reason": closure_reason,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error cerrando leads manualmente: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Función de utilidad para registrar el blueprint
def register_scheduler_api(app):
    """Registra el blueprint del scheduler en la aplicación Flask."""
    app.register_blueprint(api_scheduler)
    logger.info("API del scheduler registrada en /api/scheduler/*")
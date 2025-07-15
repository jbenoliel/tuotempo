"""
API REST para gestión de llamadas automáticas con Pearl AI.
Proporciona endpoints para controlar el sistema de llamadas desde la interfaz web.
"""

from flask import Flask, request, jsonify, Blueprint
import logging
import json
from datetime import datetime
from typing import Dict, List

from db import get_connection
from call_manager import (CallManager, get_call_manager, CallStatus, set_override_phone)
from pearl_caller import get_pearl_client, PearlAPIError

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint para las APIs de llamadas
api_pearl_calls = Blueprint('api_pearl_calls', __name__, url_prefix='/api/calls')

@api_pearl_calls.route('/status', methods=['GET'])
def get_call_system_status():
    """
    Obtiene el estado actual del sistema de llamadas.
    
    Returns:
        JSON: Estado del gestor, estadísticas y configuración
    """
    try:
        manager = get_call_manager()
        pearl_client = get_pearl_client()
        
        # Estado del gestor
        manager_status = manager.get_status()
        
        # Información adicional
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "system_status": {
                "call_manager": manager_status,
                "pearl_connection": pearl_client.test_connection(),
                "default_outbound_id": pearl_client.get_default_outbound_id()
            },
            "leads_summary": _get_leads_summary()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_pearl_calls.route('/start', methods=['POST'])
def start_calling_system():
    """
    Inicia el sistema de llamadas automáticas.
    
    Body JSON (opcional):
        {
            "max_concurrent": 3,
            "selected_leads": [1, 2, 3]  // IDs específicos o null para todos los seleccionados
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json() or {}
        
        manager = get_call_manager()
        
        # Verificar si ya está ejecutándose
        if manager.is_running:
            return jsonify({
                "success": False,
                "error": "El sistema de llamadas ya está en ejecución",
                "current_status": manager.get_status()
            }), 400
        
        # Configurar parámetros opcionales
        max_concurrent = data.get('max_concurrent', 3)
        selected_leads = data.get('selected_leads')
        override_phone = data.get('override_phone')
        
        # Ajustar concurrencia si se especifica
        if override_phone is not None:
            set_override_phone(override_phone)
            logger.warning(f"Modo teléfono de prueba activo: {override_phone}")
        else:
            # Si no se especifica override_phone, asegurarse de limpiar
            set_override_phone(None)

        if max_concurrent != manager.max_concurrent_calls:
            manager.max_concurrent_calls = max_concurrent
            logger.info(f"Concurrencia ajustada a {max_concurrent} llamadas simultáneas")
        
        # Si se especifican leads específicos, añadirlos a la cola
        if selected_leads:
            # Primero marcar los leads como seleccionados
            _mark_leads_for_calling(selected_leads, True)
            logger.info(f"Marcados {len(selected_leads)} leads específicos para llamar")
        
        # Configurar callbacks para eventos en tiempo real
        def on_call_started(lead_id, phone_number):
            logger.info(f"📞 Llamada iniciada: Lead {lead_id} -> {phone_number}")
        
        def on_call_completed(lead_id, phone_number, response):
            logger.info(f"✅ Llamada completada: Lead {lead_id}")
        
        def on_call_failed(lead_id, phone_number, error):
            logger.warning(f"❌ Llamada fallida: Lead {lead_id} - {error}")
        
        def on_stats_updated(stats):
            logger.debug(f" Stats: {stats}")
        
        manager.set_callbacks(
            on_call_started=on_call_started,
            on_call_completed=on_call_completed,
            on_call_failed=on_call_failed,
            on_stats_updated=on_stats_updated
        )
        
        # Iniciar el sistema
        success = manager.start_calling()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Sistema de llamadas iniciado exitosamente",
                "status": manager.get_status(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "No se pudo iniciar el sistema de llamadas",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Error iniciando sistema de llamadas: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_pearl_calls.route('/stop', methods=['POST'])
def stop_calling_system():
    """
    Detiene el sistema de llamadas automáticas.
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        manager = get_call_manager()
        
        # Verificar si está ejecutándose
        if not manager.is_running:
            return jsonify({
                "success": False,
                "error": "El sistema de llamadas no está en ejecución",
                "current_status": manager.get_status()
            }), 400
        
        # Detener el sistema
        success = manager.stop_calling()
        
        if success:
            return jsonify({
                "success": True,
                "message": "Sistema de llamadas detenido exitosamente",
                "final_stats": manager.get_status(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "No se pudo detener el sistema de llamadas completamente",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Error deteniendo sistema de llamadas: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_pearl_calls.route('/leads', methods=['GET'])
def get_leads_for_calling():
    """
    Obtiene la lista de leads disponibles para llamadas con filtros.
    
    Query parameters:
        - city: Filtrar por ciudad
        - status: Filtrar por estado de llamada
        - priority: Filtrar por prioridad
        - selected_only: true/false - Solo leads seleccionados
        - limit: Número máximo de resultados (default: 100)
        - offset: Offset para paginación (default: 0)
    
    Returns:
        JSON: Lista de leads con información relevante
    """
    try:
        # Obtener parámetros de filtro
        city = request.args.get('city')
        status = request.args.get('status')
        priority = request.args.get('priority')
        selected_only = request.args.get('selected_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Construir query dinámicamente
        conditions = []
        params = []
        
        # Filtro base: al menos un teléfono válido (telefono o telefono2)
        conditions.append("((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))")
        
        if city:
            conditions.append("ciudad LIKE %s")
            params.append(f"%{city}%")
        
        if status and status != 'todos':
            conditions.append("call_status = %s")
            params.append(status)
        
        if priority:
            conditions.append("call_priority = %s")
            params.append(int(priority))
        
        if selected_only:
            conditions.append("selected_for_calling = TRUE")
        
        # Query principal
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT 
                id, nombre, apellidos, telefono, telefono2, ciudad, codigo_postal, 
                nombre_clinica, 
                call_status, 
                call_priority, 
                selected_for_calling, 
                last_call_attempt, 
                call_attempts_count, 
                call_error_message, 
                last_call_attempt, 
                call_attempts_count, 
                updated_at
            FROM leads 
            WHERE {where_clause}
            ORDER BY call_priority ASC, updated_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        # Query para contar total
        count_query = f"SELECT COUNT(*) as total FROM leads WHERE {where_clause}"
        count_params = params[:-2]  # Excluir limit y offset
        
        conn = get_connection()
        # Hacemos un commit para asegurar que leemos el estado más reciente de la BD,
        # especialmente después de una recarga de datos en otra transacción.
        conn.commit()
        cursor = conn.cursor(dictionary=True)
        
        # Ejecutar consultas
        cursor.execute(query, params)
        leads = cursor.fetchall()
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        # Formatear fechas para JSON
        for lead in leads:
            if lead['last_call_attempt']:
                lead['last_call_attempt'] = lead['last_call_attempt'].isoformat()
            if lead['updated_at']:
                lead['updated_at'] = lead['updated_at'].isoformat()
        
        return jsonify({
            "success": True,
            "leads": leads,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "city": city,
                "status": status,
                "priority": priority,
                "selected_only": selected_only
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo leads: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if conn:
            conn.close()

@api_pearl_calls.route('/leads/select', methods=['POST'])
def select_leads_for_calling():
    """
    Marca/desmarca leads para el sistema de llamadas.
    
    Body JSON:
        {
            "lead_ids": [1, 2, 3],
            "selected": true,
            "priority": 3  // opcional, para establecer prioridad
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json()
        
        if not data or 'lead_ids' not in data:
            return jsonify({
                "success": False,
                "error": "Se requiere 'lead_ids' en el body"
            }), 400
        
        lead_ids = data['lead_ids']
        selected = data.get('selected', True)
        priority = data.get('priority')
        
        if not isinstance(lead_ids, list) or not lead_ids:
            return jsonify({
                "success": False,
                "error": "lead_ids debe ser una lista no vacía"
            }), 400
        
        # Actualizar base de datos
        updated_count = _mark_leads_for_calling(lead_ids, selected, priority)
        
        return jsonify({
            "success": True,
            "message": f"Actualizados {updated_count} leads",
            "updated_count": updated_count,
            "operation": "selected" if selected else "deselected",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error seleccionando leads: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_pearl_calls.route('/leads/reset', methods=['POST'])
def reset_leads_status():
    """
    Reinicia el estado de llamadas de leads específicos o todos.
    
    Body JSON:
        {
            "lead_ids": [1, 2, 3],  // opcional, si no se especifica aplica a todos
            "reset_attempts": true,  // opcional, reiniciar contador de intentos
            "reset_selection": false  // opcional, quitar selección
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json() or {}
        
        lead_ids = data.get('lead_ids')
        reset_attempts = data.get('reset_attempts', True)
        reset_selection = data.get('reset_selection', False)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir query de actualización
        update_fields = [
            "call_status = 'no_selected'",
            "call_error_message = NULL",
            "last_call_attempt = NULL",
            "updated_at = CURRENT_TIMESTAMP"
        ]
        
        if reset_attempts:
            update_fields.append("call_attempts_count = 0")
        
        if reset_selection:
            update_fields.append("selected_for_calling = FALSE")
        
        # Condición WHERE
        if lead_ids:
            placeholders = ','.join(['%s'] * len(lead_ids))
            where_clause = f"id IN ({placeholders})"
            params = lead_ids
        else:
            where_clause = "1=1"  # Todos los leads
            params = []
        
        query = f"UPDATE leads SET {', '.join(update_fields)} WHERE {where_clause}"
        
        cursor.execute(query, params)
        updated_count = cursor.rowcount
        conn.commit()
        
        return jsonify({
            "success": True,
            "message": f"Reiniciado estado de {updated_count} leads",
            "updated_count": updated_count,
            "reset_attempts": reset_attempts,
            "reset_selection": reset_selection,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error reiniciando estado de leads: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if conn:
            conn.close()

@api_pearl_calls.route('/pearl/campaigns', methods=['GET'])
def get_pearl_campaigns():
    """
    Obtiene las campañas outbound disponibles en Pearl AI.
    
    Returns:
        JSON: Lista de campañas outbound
    """
    try:
        pearl_client = get_pearl_client()
        
        # Probar conexión primero
        if not pearl_client.test_connection():
            return jsonify({
                "success": False,
                "error": "No se puede conectar con Pearl AI",
                "timestamp": datetime.now().isoformat()
            }), 503
        
        # Obtener campañas
        campaigns = pearl_client.get_outbound_campaigns()
        
        return jsonify({
            "success": True,
            "campaigns": campaigns,
            "total_campaigns": len(campaigns),
            "default_outbound_id": pearl_client.get_default_outbound_id(),
            "timestamp": datetime.now().isoformat()
        })
        
    except PearlAPIError as e:
        logger.error(f"Error de API Pearl: {e}")
        return jsonify({
            "success": False,
            "error": f"Error de Pearl AI: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 502
    except Exception as e:
        logger.error(f"Error obteniendo campañas Pearl: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500




@api_pearl_calls.route('/test/connection', methods=['GET'])
def test_pearl_connection():
    """
    Prueba la conexión con Pearl AI.
    
    Returns:
        JSON: Resultado de la prueba de conexión
    """
    try:
        pearl_client = get_pearl_client()
        
        # Probar conexión
        connection_ok = pearl_client.test_connection()
        
        response = {
            "success": True,
            "pearl_connection": connection_ok,
            "default_outbound_id": pearl_client.get_default_outbound_id(),
            "timestamp": datetime.now().isoformat()
        }
        
        if connection_ok:
            # Si la conexión funciona, obtener info adicional
            try:
                campaigns = pearl_client.get_outbound_campaigns()
                response["available_campaigns"] = len(campaigns)
            except:
                response["available_campaigns"] = "Error obteniendo campañas"
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error probando conexión Pearl: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "pearl_connection": False,
            "timestamp": datetime.now().isoformat()
        }), 500

# Funciones auxiliares
def _get_leads_summary() -> Dict:
    """Obtiene resumen de leads para el dashboard."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Consulta de resumen
        query = """
            SELECT 
                call_status,
                COUNT(*) as count,
                SUM(CASE WHEN selected_for_calling = TRUE THEN 1 ELSE 0 END) as selected_count
            FROM leads 
            WHERE telefono IS NOT NULL AND telefono != ''
            GROUP BY call_status
            ORDER BY call_status
        """
        
        cursor.execute(query)
        status_summary = cursor.fetchall()
        
        # Consulta de totales
        cursor.execute("""
            SELECT 
                COUNT(*) as total_leads,
                SUM(CASE WHEN selected_for_calling = TRUE THEN 1 ELSE 0 END) as total_selected,
                SUM(CASE WHEN telefono IS NOT NULL AND telefono != '' THEN 1 ELSE 0 END) as leads_with_phone
            FROM leads
        """)
        totals = cursor.fetchone()
        
        return {
            "status_breakdown": status_summary,
            "totals": totals
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen de leads: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def _mark_leads_for_calling(lead_ids: List[int], selected: bool, priority: int = None) -> int:
    """Marca/desmarca leads para llamadas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir query de actualización
        update_fields = [
            "selected_for_calling = %s",
            "updated_at = CURRENT_TIMESTAMP"
        ]
        params = [selected]
        
        if priority is not None:
            update_fields.append("call_priority = %s")
            params.append(priority)
        
        # Si se está seleccionando, resetear estado de error
        if selected:
            update_fields.extend([
                "call_status = 'selected'",
                "call_error_message = NULL"
            ])
        
        # Añadir condición WHERE
        placeholders = ','.join(['%s'] * len(lead_ids))
        query = f"""
            UPDATE leads SET {', '.join(update_fields)}
            WHERE id IN ({placeholders})
            AND telefono IS NOT NULL AND telefono != ''
        """
        params.extend(lead_ids)
        
        cursor.execute(query, params)
        updated_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Marcados {updated_count} leads como {'seleccionados' if selected else 'no seleccionados'}")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error marcando leads: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Función para registrar el blueprint en la app principal
def register_calls_api(app: Flask):
    """Registra la API de llamadas en la aplicación Flask."""
    app.register_blueprint(api_pearl_calls)
    logger.info("API de llamadas registrada en /api/calls")

if __name__ == "__main__":
    # Código de prueba
    from flask import Flask
    
    app = Flask(__name__)
    register_calls_api(app)
    
    print("🧪 Probando API de llamadas...")
    print("Ejecuta la app y visita:")
    print("  GET /api/calls/status")
    print("  GET /api/calls/test/connection")
    print("  GET /api/calls/leads")
    
    app.run(debug=True, port=5001)

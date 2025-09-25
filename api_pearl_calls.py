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
from call_manager import (CallManager, get_call_manager, CallStatus, set_override_phone, get_override_phone)
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
        logger.info(f"Petición de inicio recibida: {data}")
        
        manager = get_call_manager()
        
        # Verificar si ya está ejecutándose
        if manager.is_running:
            logger.warning("Sistema ya en ejecución")
            return jsonify({
                "success": False,
                "error": "El sistema de llamadas ya está en ejecución",
                "current_status": manager.get_status()
            }), 400
        
        # Configurar parámetros opcionales
        max_concurrent = data.get('max_concurrent', 3)
        selected_leads = data.get('selected_leads')
        override_phone = data.get('override_phone')
        
        logger.info(f"🔧 CONFIGURACIÓN RECIBIDA:")
        logger.info(f"   - max_concurrent: {max_concurrent}")
        logger.info(f"   - selected_leads: {selected_leads}")
        logger.info(f"   - override_phone: {override_phone}")
        
        # Ajustar concurrencia si se especifica
        if override_phone is not None:
            logger.warning(f"🧪 ACTIVANDO MODO PRUEBA...")
            logger.info(f"📞 Teléfono de prueba recibido: '{override_phone}'")
            # Normalizar el teléfono de prueba también
            from call_manager import normalize_spanish_phone
            normalized_override = normalize_spanish_phone(override_phone) if override_phone else override_phone
            set_override_phone(normalized_override)
            logger.warning(f"🧪 MODO PRUEBA CONFIGURADO: {override_phone} -> {normalized_override}")
            from call_manager import get_override_phone
            verification = get_override_phone()
            logger.info(f"✅ VERIFICACIÓN - Override phone global: {verification}")
        else:
            logger.info(f"🔄 Limpiando modo prueba (override_phone es None)")
            # Si no se especifica override_phone, asegurarse de limpiar
            set_override_phone(None)
            from call_manager import get_override_phone
            verification = get_override_phone()
            logger.info(f"✅ VERIFICACIÓN - Override phone limpiado: {verification}")

        if max_concurrent != manager.max_concurrent_calls:
            manager.max_concurrent_calls = max_concurrent
            logger.info(f"Concurrencia ajustada a {max_concurrent} llamadas simultáneas")
        
        # Ya no necesitamos marcar leads en la BD cuando usamos IDs específicos
        # CallManager ahora trabajará directamente con la lista de IDs
        if selected_leads:
            logger.info(f"📋 Se procesarán {len(selected_leads)} leads específicos: {selected_leads}")
        else:
            logger.info("📋 Se procesarán todos los leads marcados como selected_for_calling=TRUE")
        
        # Configurar callbacks para eventos en tiempo real
        def on_call_started(lead_id, phone_number):
            logger.info(f"📞 Llamada iniciada: Lead {lead_id} -> {phone_number}")
            
            # Deseleccionar el lead en la base de datos
            try:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE leads SET selected_for_calling = FALSE WHERE id = %s",
                        (lead_id,)
                    )
                    conn.commit()
                    logger.info(f"✅ Lead {lead_id} deseleccionado automáticamente tras iniciar llamada")
            except Exception as e:
                logger.error(f"❌ Error al deseleccionar lead {lead_id}: {e}")
        
        def on_call_completed(lead_id, phone_number, response):
            logger.info(f"✅ Llamada completada: Lead {lead_id}")
            
            # Integración con el sistema de scheduling para llamadas completadas
            try:
                from call_manager_scheduler_integration import enhanced_process_call_result
                
                # Crear un resultado de llamada exitoso para el sistema de scheduling
                call_result = {
                    'success': True,
                    'status': 'completed',
                    'lead_id': lead_id,
                    'phone_number': phone_number,
                    'response': response
                }
                
                # Procesar el resultado usando el sistema de integración
                enhanced_process_call_result(lead_id, call_result, pearl_response=response)
                logger.info(f"✅ Sistema de scheduling procesó la llamada exitosa para lead {lead_id}")
                
            except Exception as e:
                logger.error(f"❌ Error integrando con scheduler para lead {lead_id}: {e}")
        
        def on_call_failed(lead_id, phone_number, error):
            logger.warning(f"❌ Llamada fallida: Lead {lead_id} - {error}")
            
            # Integración con el sistema de scheduling para llamadas fallidas
            try:
                from call_manager_scheduler_integration import enhanced_process_call_result
                
                # Crear un resultado de llamada simulado para el sistema de scheduling
                call_result = {
                    'success': False,
                    'status': 'failed',
                    'error_message': str(error),
                    'lead_id': lead_id,
                    'phone_number': phone_number
                }
                
                # Procesar el resultado usando el sistema de integración
                enhanced_process_call_result(lead_id, call_result)
                logger.info(f"🔄 Sistema de scheduling procesó la llamada fallida para lead {lead_id}")
                
            except Exception as e:
                logger.error(f"❌ Error integrando con scheduler para lead {lead_id}: {e}")
        
        def on_stats_updated(stats):
            logger.debug(f" Stats: {stats}")
        
        manager.set_callbacks(
            on_call_started=on_call_started,
            on_call_completed=on_call_completed,
            on_call_failed=on_call_failed,
            on_stats_updated=on_stats_updated
        )
        
        # Iniciar el sistema
        logger.info("Intentando iniciar sistema de llamadas...")
        if selected_leads:
            logger.info(f"🎯 Iniciando con leads específicos: {selected_leads}")
            success = manager.start_calling(specific_lead_ids=selected_leads)
        else:
            logger.info("📋 Iniciando con todos los leads marcados")
            success = manager.start_calling()
        
        if success:
            logger.info("✅ Sistema iniciado exitosamente")
            return jsonify({
                "success": True,
                "message": "Sistema de llamadas iniciado exitosamente",
                "status": manager.get_status(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            logger.error("❌ No se pudo iniciar el sistema")
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
        logger.info("Petición de parada recibida")
        manager = get_call_manager()
        
        # Verificar si está ejecutándose
        if not manager.is_running:
            logger.warning("Sistema no está en ejecución")
            return jsonify({
                "success": False,
                "error": "El sistema de llamadas no está en ejecución",
                "current_status": manager.get_status()
            }), 400
        
        # Detener el sistema
        logger.info("Intentando detener sistema de llamadas...")
        success = manager.stop_calling()
        
        if success:
            logger.info("✅ Sistema detenido exitosamente")
            return jsonify({
                "success": True,
                "message": "Sistema de llamadas detenido exitosamente",
                "final_stats": manager.get_status(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            logger.error("❌ No se pudo detener el sistema completamente")
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
        - estado1: Filtrar por status_level_1 (estado)
        - estado2: Filtrar por status_level_2 (subestado)
        - selected_only: true/false - Solo leads seleccionados
        - origen_archivo: Filtrar por archivo de origen (puede ser múltiple)
        - limit: Número máximo de resultados (default: 100)
        - offset: Offset para paginación (default: 0)
    
    Returns:
        JSON: Lista de leads con información relevante
    """
    try:
        # Obtener parámetros de filtro
        city = request.args.get('city')
        status = request.args.get('status')
        priority = request.args.get('priority')  # puede ser None o ''
        estado1 = request.args.get('estado1')
        estado2 = request.args.get('estado2')
        selected_only = request.args.get('selected_only', 'false').lower() == 'true'
        origen_archivos = request.args.getlist('origen_archivo')  # Múltiples valores
        limit = int(request.args.get('limit', 25))
        offset = int(request.args.get('offset', 0))
        
        # Construir query dinámicamente
        conditions = []
        params = []
        
        # Filtro base: al menos un teléfono válido (telefono o telefono2)
        conditions.append("((l.telefono IS NOT NULL AND l.telefono != '') OR (l.telefono2 IS NOT NULL AND l.telefono2 != ''))")
        
        # Filtro: excluir leads gestionados manualmente
        conditions.append("(l.manual_management IS NULL OR l.manual_management = FALSE)")
        
        if city:
            conditions.append("l.ciudad LIKE %s")
            params.append(f"%{city}%")
        
        if status and status != 'todos':
            conditions.append("l.call_status = %s")
            params.append(status)
        
        if priority not in (None, '', 'todos'):
            try:
                priority_int = int(priority)
                conditions.append("l.call_priority = %s")
                params.append(priority_int)
            except ValueError:
                logger.warning(f"Parámetro 'priority' inválido: {priority}")
        
        if estado1 and estado1 != '':
            conditions.append("l.status_level_1 = %s")
            params.append(estado1)
        
        if estado2 and estado2 != '':
            conditions.append("l.status_level_2 = %s")
            params.append(estado2)
        
        if selected_only:
            conditions.append("l.selected_for_calling = TRUE")
        
        # Filtro por archivo de origen (múltiple)
        if origen_archivos:
            origen_archivos = [archivo for archivo in origen_archivos if archivo.strip()]  # Filtrar vacíos
            if origen_archivos:
                placeholders = ', '.join(['%s'] * len(origen_archivos))
                conditions.append(f"l.origen_archivo IN ({placeholders})")
                params.extend(origen_archivos)
        
        # Query principal
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT 
                l.id, l.nombre, l.apellidos, l.telefono, l.telefono2, l.ciudad, l.codigo_postal, 
                l.nombre_clinica, 
                l.call_status, 
                l.call_priority, 
                l.selected_for_calling, 
                l.last_call_attempt, 
                l.call_attempts_count, 
                l.call_error_message, 
                l.status_level_1, 
                l.status_level_2,
                l.manual_management,
                l.updated_at,
                COALESCE(pc.call_count, 0) as call_count,
                COALESCE(pc.total_duration, 0) as total_duration,
                pc.last_call_time,
                pc.calls_with_recording
            FROM leads l
            LEFT JOIN (
                SELECT 
                    lead_id,
                    COUNT(*) as call_count,
                    SUM(duration) as total_duration,
                    MAX(call_time) as last_call_time,
                    COUNT(CASE WHEN recording_url IS NOT NULL THEN 1 END) as calls_with_recording
                FROM pearl_calls 
                GROUP BY lead_id
            ) pc ON l.id = pc.lead_id
            WHERE {where_clause}
            ORDER BY l.call_priority ASC, l.updated_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        # Query para contar total
        count_query = f"SELECT COUNT(*) as total FROM leads l WHERE {where_clause}"
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

@api_pearl_calls.route('/leads/manual-management', methods=['POST'])
def toggle_manual_management():
    """
    Cambia el estado de gestión manual de uno o varios leads.
    
    Body JSON:
        {
            "lead_ids": [1, 2, 3],  // IDs de los leads
            "manual_management": true  // true = gestión manual, false = gestión automática
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json() or {}
        
        lead_ids = data.get('lead_ids')
        manual_management = data.get('manual_management')
        
        if not isinstance(lead_ids, list) or not lead_ids:
            return jsonify({
                "success": False,
                "error": "lead_ids debe ser una lista no vacía"
            }), 400
        
        if manual_management is None:
            return jsonify({
                "success": False,
                "error": "manual_management es requerido (true/false)"
            }), 400
        
        # Actualizar base de datos
        conn = get_connection()
        cursor = conn.cursor()
        
        # Preparar query
        placeholders = ','.join(['%s'] * len(lead_ids))
        query = f"""
            UPDATE leads 
            SET manual_management = %s, updated_at = NOW()
            WHERE id IN ({placeholders})
        """
        
        params = [manual_management] + lead_ids
        cursor.execute(query, params)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Actualizados {updated_count} leads - gestión manual: {manual_management}")
        
        return jsonify({
            "success": True,
            "message": f"Actualizados {updated_count} leads",
            "updated_count": updated_count,
            "manual_management": manual_management,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error actualizando gestión manual: {e}")
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




@api_pearl_calls.route('/configuration', methods=['GET'])
def get_call_configuration():
    """
    Obtiene la configuración actual del sistema de llamadas.
    
    Returns:
        JSON: Configuración actual
    """
    try:
        manager = get_call_manager()
        override_phone = get_override_phone()
        
        config = {
            "maxConcurrentCalls": getattr(manager, 'max_concurrent_calls', 3),
            "retryAttempts": getattr(manager, 'max_retry_attempts', 3),
            "retryDelay": getattr(manager, 'retry_delay_seconds', 30),
            "testMode": override_phone is not None,
            "overridePhone": override_phone
        }
        
        return jsonify({
            "success": True,
            "configuration": config,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_pearl_calls.route('/configuration', methods=['POST'])
def save_call_configuration():
    """
    Guarda la configuración del sistema de llamadas.
    
    Body JSON:
        {
            "maxConcurrentCalls": 3,
            "retryAttempts": 3,
            "retryDelay": 30
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Se requiere configuración en el body"
            }), 400
        
        manager = get_call_manager()
        
        # Actualizar configuración del manager
        if 'maxConcurrentCalls' in data:
            max_concurrent = int(data['maxConcurrentCalls'])
            if 1 <= max_concurrent <= 10:  # Límite razonable
                manager.max_concurrent_calls = max_concurrent
            else:
                return jsonify({
                    "success": False,
                    "error": "maxConcurrentCalls debe estar entre 1 y 10"
                }), 400
        
        if 'retryAttempts' in data:
            retry_attempts = int(data['retryAttempts'])
            if 0 <= retry_attempts <= 10:
                manager.max_retry_attempts = retry_attempts
            else:
                return jsonify({
                    "success": False,
                    "error": "retryAttempts debe estar entre 0 y 10"
                }), 400
        
        if 'retryDelay' in data:
            retry_delay = int(data['retryDelay'])
            if 10 <= retry_delay <= 3600:  # Entre 10 segundos y 1 hora
                manager.retry_delay_seconds = retry_delay
            else:
                return jsonify({
                    "success": False,
                    "error": "retryDelay debe estar entre 10 y 3600 segundos"
                }), 400
        
        logger.info(f"Configuración actualizada: {data}")
        
        # Obtener configuración actualizada para respuesta
        updated_config = {
            "maxConcurrentCalls": manager.max_concurrent_calls,
            "retryAttempts": getattr(manager, 'max_retry_attempts', 3),
            "retryDelay": getattr(manager, 'retry_delay_seconds', 30)
        }
        
        return jsonify({
            "success": True,
            "message": "Configuración guardada correctamente",
            "configuration": updated_config,
            "timestamp": datetime.now().isoformat()
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"Valor inválido: {str(e)}"
        }), 400
    except Exception as e:
        logger.error(f"Error guardando configuración: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_pearl_calls.route('/test-connection', methods=['GET'])
def test_pearl_connection_simple():
    """
    Prueba la conexión con Pearl AI (endpoint simplificado).
    
    Returns:
        JSON: Resultado de la prueba de conexión
    """
    try:
        pearl_client = get_pearl_client()
        
        # Probar conexión
        connection_ok = pearl_client.test_connection()
        
        if connection_ok:
            return jsonify({
                "success": True,
                "pearl_connection": True,
                "message": "Conexión con Pearl AI exitosa",
                "default_outbound_id": pearl_client.get_default_outbound_id(),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "pearl_connection": False,
                "error": "No se pudo conectar con Pearl AI",
                "timestamp": datetime.now().isoformat()
            }), 503
        
    except Exception as e:
        logger.error(f"Error probando conexión Pearl: {e}")
        return jsonify({
            "success": False,
            "pearl_connection": False,
            "error": f"Error de conexión: {str(e)}",
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
              AND (manual_management IS NULL OR manual_management = FALSE)
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
                SUM(CASE WHEN telefono IS NOT NULL AND telefono != '' THEN 1 ELSE 0 END) as leads_with_phone,
                SUM(CASE WHEN manual_management = TRUE THEN 1 ELSE 0 END) as manually_managed
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
        
        # Si se está seleccionando, resetear estado de error pero mantener no_selected
        if selected:
            update_fields.extend([
                "call_status = 'no_selected'",  # Listo para llamar, no "selected"
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

@api_pearl_calls.route('/admin/cleanup-selected', methods=['POST'])
def cleanup_selected_leads():
    """
    ENDPOINT DE EMERGENCIA: Limpia todos los leads marcados para llamada
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Ver cuántos leads están marcados
        cursor.execute("SELECT COUNT(*) AS count FROM leads WHERE selected_for_calling = 1")
        count_before = cursor.fetchone()['count']
        
        if count_before == 0:
            return jsonify({
                "success": True, 
                "message": "No hay leads marcados para limpiar",
                "cleaned_count": 0
            })
        
        # Obtener ejemplos antes de limpiar
        cursor.execute("""
            SELECT id, nombre, telefono, call_status 
            FROM leads 
            WHERE selected_for_calling = 1 
            LIMIT 5
        """)
        examples = cursor.fetchall()
        
        # Limpiar todos los leads marcados
        cursor.execute("""
            UPDATE leads 
            SET selected_for_calling = 0,
                call_status = 'no_selected'
            WHERE selected_for_calling = 1
        """)
        
        cleaned_count = cursor.rowcount
        conn.commit()
        
        # Verificar limpieza
        cursor.execute("SELECT COUNT(*) AS count FROM leads WHERE selected_for_calling = 1")
        count_after = cursor.fetchone()['count']
        
        logger.warning(f"🧹 LIMPIEZA DE EMERGENCIA: {cleaned_count} leads limpiados")
        
        return jsonify({
            "success": True,
            "message": f"Limpieza completada exitosamente",
            "leads_before": count_before,
            "cleaned_count": cleaned_count,
            "leads_after": count_after,
            "examples_cleaned": [
                f"ID:{ex['id']} {ex.get('nombre','')} {ex.get('telefono','')}" 
                for ex in examples
            ]
        })
        
    except Exception as e:
        logger.error(f"Error en limpieza de emergencia: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/leads/mark-no-interesado', methods=['POST'])
def mark_no_interesado():
    """
    Marca uno o varios leads como 'No Interesado'.

    Body JSON:
        {
            "lead_ids": [1,2,3],
            "subreason": "No da motivos"   # opcional (status_level_2)
        }

    Efectos en BD:
      - status_level_1 = 'No Interesado'
      - status_level_2 = subreason (o 'No da motivos' por defecto)
      - lead_status = 'closed'
      - closure_reason = 'No interesado'
      - selected_for_calling = FALSE
      - updated_at = NOW()
    """
    try:
        data = request.get_json() or {}
        lead_ids = data.get('lead_ids')
        subreason = (data.get('subreason') or 'No da motivos').strip()

        if not isinstance(lead_ids, list) or not lead_ids:
            return jsonify({
                "success": False,
                "error": "lead_ids debe ser una lista no vacía"
            }), 400

        conn = get_connection()
        if not conn:
            return jsonify({"success": False, "error": "Error de conexión a la BD"}), 500
        cursor = conn.cursor()

        placeholders = ','.join(['%s'] * len(lead_ids))
        query = f"""
            UPDATE leads
            SET status_level_1 = 'No Interesado',
                status_level_2 = %s,
                lead_status = 'closed',
                closure_reason = 'No interesado',
                selected_for_calling = FALSE,
                updated_at = NOW()
            WHERE id IN ({placeholders})
        """
        params = [subreason] + lead_ids
        cursor.execute(query, params)
        updated_count = cursor.rowcount
        conn.commit()

        logger.info(f"Marcados {updated_count} leads como 'No Interesado' (sub: {subreason})")
        return jsonify({
            "success": True,
            "updated_count": updated_count,
            "message": f"{updated_count} leads marcados como 'No Interesado'"
        })
    except Exception as e:
        logger.error(f"Error marcando No Interesado: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/history', methods=['GET'])
def get_calls_history():
    """
    Obtiene el historial detallado de llamadas desde la tabla pearl_calls.
    
    Parámetros de query:
    - limit: Número máximo de registros (default 50, max 200)
    - offset: Número de registros a saltar para paginación (default 0)
    - lead_id: Filtrar por ID de lead específico
    - status: Filtrar por status de llamada
    - from_date: Fecha desde (YYYY-MM-DD)
    - to_date: Fecha hasta (YYYY-MM-DD)
    """
    try:
        # Parámetros de consulta
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        lead_id = request.args.get('lead_id')
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Construir query base
        base_query = """
            SELECT 
                pc.id,
                pc.call_id,
                pc.phone_number,
                pc.lead_id,
                l.nombre,
                l.apellidos,
                pc.outbound_id,
                pc.call_time,
                pc.start_time,
                pc.end_time,
                pc.duration,
                pc.status,
                pc.outcome,
                pc.summary,
                pc.transcription,
                pc.recording_url,
                pc.cost,
                pc.created_at,
                pc.updated_at
            FROM pearl_calls pc
            LEFT JOIN leads l ON pc.lead_id = l.id
        """
        
        # Construir filtros WHERE
        where_conditions = []
        params = []
        
        if lead_id:
            where_conditions.append("pc.lead_id = %s")
            params.append(lead_id)
            
        if status:
            where_conditions.append("pc.status = %s")
            params.append(status)
            
        if from_date:
            where_conditions.append("DATE(pc.call_time) >= %s")
            params.append(from_date)
            
        if to_date:
            where_conditions.append("DATE(pc.call_time) <= %s")
            params.append(to_date)
        
        # Añadir WHERE si hay condiciones
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
            
        # Ordenar y paginar
        base_query += " ORDER BY pc.call_time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Ejecutar query principal
        cursor.execute(base_query, params)
        calls = cursor.fetchall()
        
        # Query para contar total (sin paginación) - excluir LIMIT y OFFSET
        count_query = "SELECT COUNT(*) as total FROM pearl_calls pc"
        if where_conditions:
            count_query += " WHERE " + " AND ".join(where_conditions)
            count_params = params[:-2]  # Remover limit y offset
        else:
            count_params = []
            
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        # Formatear respuesta
        response = {
            'calls': calls,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'count': len(calls)
            },
            'filters': {
                'lead_id': lead_id,
                'status': status,
                'from_date': from_date,
                'to_date': to_date
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo historial de llamadas: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/history/stats', methods=['GET'])
def get_calls_stats():
    """
    Obtiene estadísticas resumidas del historial de llamadas.
    """
    try:
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Estadísticas generales
        stats_query = """
            SELECT 
                COUNT(*) as total_calls,
                COUNT(DISTINCT lead_id) as unique_leads,
                AVG(duration) as avg_duration,
                SUM(cost) as total_cost,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_calls,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_calls,
                COUNT(CASE WHEN outcome = 'answered' THEN 1 END) as answered_calls,
                COUNT(CASE WHEN outcome = 'no_answer' THEN 1 END) as no_answer_calls
            FROM pearl_calls
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        # Estadísticas por día (últimos 7 días)
        daily_stats_query = """
            SELECT 
                DATE(call_time) as call_date,
                COUNT(*) as calls_count,
                AVG(duration) as avg_duration
            FROM pearl_calls 
            WHERE call_time >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
            GROUP BY DATE(call_time)
            ORDER BY call_date DESC
        """
        
        cursor.execute(daily_stats_query)
        daily_stats = cursor.fetchall()
        
        # Estadísticas por resultado
        outcome_stats_query = """
            SELECT 
                outcome,
                COUNT(*) as count
            FROM pearl_calls 
            WHERE outcome IS NOT NULL
            GROUP BY outcome
            ORDER BY count DESC
        """
        
        cursor.execute(outcome_stats_query)
        outcome_stats = cursor.fetchall()
        
        response = {
            'general': stats,
            'daily': daily_stats,
            'outcomes': outcome_stats
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de llamadas: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/schedule', methods=['GET'])
def get_scheduled_calls():
    """
    Obtiene las llamadas programadas desde la tabla call_schedule.
    
    Parámetros de query:
    - limit: Número máximo de registros (default 50, max 200)
    - offset: Número de registros a saltar para paginación (default 0)
    - status: Filtrar por status ('pending', 'completed', 'failed', 'cancelled')
    - lead_id: Filtrar por ID de lead específico
    - from_date: Fecha desde (YYYY-MM-DD)
    - to_date: Fecha hasta (YYYY-MM-DD)
    """
    try:
        # Parámetros de consulta
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')
        lead_id = request.args.get('lead_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Construir query base
        base_query = """
            SELECT 
                cs.id,
                cs.lead_id,
                l.nombre,
                l.apellidos,
                l.telefono,
                l.ciudad,
                cs.scheduled_at,
                cs.attempt_number,
                cs.status,
                cs.last_outcome,
                cs.created_at,
                cs.updated_at,
                l.call_attempts_count,
                l.lead_status,
                l.closure_reason
            FROM call_schedule cs
            LEFT JOIN leads l ON cs.lead_id = l.id
        """
        
        # Construir filtros WHERE
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("cs.status = %s")
            params.append(status)
            
        if lead_id:
            where_conditions.append("cs.lead_id = %s")
            params.append(lead_id)
            
        if from_date:
            where_conditions.append("DATE(cs.scheduled_at) >= %s")
            params.append(from_date)
            
        if to_date:
            where_conditions.append("DATE(cs.scheduled_at) <= %s")
            params.append(to_date)
        
        # Añadir WHERE si hay condiciones
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
            
        # Ordenar y paginar
        base_query += " ORDER BY cs.scheduled_at ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Ejecutar query principal
        cursor.execute(base_query, params)
        scheduled_calls = cursor.fetchall()
        
        # Query para contar total (sin paginación)
        count_query = "SELECT COUNT(*) as total FROM call_schedule cs"
        if where_conditions:
            count_query += " WHERE " + " AND ".join(where_conditions)
            count_params = params[:-2]  # Remover limit y offset
        else:
            count_params = []
            
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        # Estadísticas adicionales
        stats_query = """
            SELECT 
                status,
                COUNT(*) as count
            FROM call_schedule 
            GROUP BY status
            ORDER BY status
        """
        cursor.execute(stats_query)
        status_stats = cursor.fetchall()
        
        # Formatear respuesta
        response = {
            'scheduled_calls': scheduled_calls,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'count': len(scheduled_calls)
            },
            'status_breakdown': status_stats,
            'filters': {
                'status': status,
                'lead_id': lead_id,
                'from_date': from_date,
                'to_date': to_date
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error obteniendo llamadas programadas: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/call-history/<int:lead_id>', methods=['GET'])
def get_call_history(lead_id):
    """
    Obtiene el historial completo de llamadas para un lead específico.
    
    Args:
        lead_id: ID del lead
        
    Returns:
        JSON: Historial de llamadas con grabaciones, resúmenes y transcripciones
    """
    try:
        logger.info(f"Obteniendo historial de llamadas para lead {lead_id}")
        
        conn = get_connection()
        if not conn:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información del lead
        cursor.execute("""
            SELECT nombre, apellidos, telefono, telefono2
            FROM leads 
            WHERE id = %s
        """, (lead_id,))
        
        lead_info = cursor.fetchone()
        if not lead_info:
            return jsonify({'error': 'Lead no encontrado'}), 404
        
        # Obtener historial de llamadas desde pearl_calls
        cursor.execute("""
            SELECT 
                call_id,
                phone_number,
                call_time,
                duration,
                summary,
                collected_info,
                recording_url,
                status,
                outcome,
                cost,
                transcription,
                start_time,
                end_time,
                created_at
            FROM pearl_calls 
            WHERE lead_id = %s 
            ORDER BY call_time DESC
        """, (lead_id,))
        
        calls = cursor.fetchall()
        
        # Convertir datetime a string para JSON
        for call in calls:
            for field in ['call_time', 'start_time', 'end_time', 'created_at']:
                if call.get(field):
                    call[field] = call[field].isoformat()
        
        # Obtener estadísticas adicionales
        cursor.execute("""
            SELECT 
                COUNT(*) as call_count,
                SUM(duration) as total_duration,
                MAX(call_time) as last_call_time,
                COUNT(CASE WHEN recording_url IS NOT NULL THEN 1 END) as calls_with_recording
            FROM pearl_calls 
            WHERE lead_id = %s
        """, (lead_id,))
        
        stats = cursor.fetchone()
        if stats:
            for field in ['last_call_time']:
                if stats.get(field):
                    stats[field] = stats[field].isoformat()
        
        logger.info(f"Historial obtenido: {len(calls)} llamadas para lead {lead_id}")
        
        return jsonify({
            'success': True,
            'lead_info': lead_info,
            'calls': calls,
            'stats': stats,
            'count': len(calls)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial de llamadas para lead {lead_id}: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/leads/count-by-status', methods=['GET'])
def count_leads_by_status():
    """
    Cuenta leads que coincidan con un estado específico y filtros de archivo origen.
    
    Query parameters:
        status_field: Campo de estado (ej: 'status_level_1', 'call_status')
        status_value: Valor del estado (ej: 'Volver a llamar')
        archivo_origen: Lista de archivos origen para filtrar
    
    Returns:
        JSON: {total_count: int, selected_count: int}
    """
    try:
        status_field = request.args.get('status_field', 'status_level_1')
        status_value = request.args.get('status_value', '')
        archivo_origen = request.args.getlist('archivo_origen')
        
        if not status_value:
            return jsonify({'error': 'status_value es requerido'}), 400
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Construir query base
        where_conditions = [f"TRIM({status_field}) = %s"]
        params = [status_value]

        # CRÍTICO: Solo leads OPEN - NO contar leads cerrados
        where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")

        # TEMPORAL: Incluir leads con estado 'selected' que deberían ser 'no_selected'
        where_conditions.append("(call_status = 'no_selected' OR call_status = 'selected')")

        # CRÍTICO: Excluir leads con cita programada SOLO si no es "Volver a llamar"
        # Si es "Volver a llamar", contar todas independientemente del status_level_2
        if status_value != 'Volver a llamar':
            where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")

        # Agregar filtro de archivo origen si se especifica
        if archivo_origen:
            # Usar LIKE con TRIM para manejar espacios y variaciones
            archivo_conditions = []
            for archivo in archivo_origen:
                archivo_conditions.append("TRIM(origen_archivo) LIKE %s")
                params.append(f"%{archivo}%")

            where_conditions.append(f"({' OR '.join(archivo_conditions)})")
        
        where_clause = ' AND '.join(where_conditions)
        
        # Contar total que coincide con el filtro
        query_total = f"SELECT COUNT(*) as total FROM leads WHERE {where_clause}"
        cursor.execute(query_total, params)
        total_count = cursor.fetchone()['total']
        
        # Contar cuántos ya están seleccionados
        where_conditions.append("selected_for_calling = 1")
        where_clause_selected = ' AND '.join(where_conditions)
        query_selected = f"SELECT COUNT(*) as selected FROM leads WHERE {where_clause_selected}"
        cursor.execute(query_selected, params)
        selected_count = cursor.fetchone()['selected']
        
        return jsonify({
            'success': True,
            'total_count': total_count,
            'selected_count': selected_count,
            'not_selected_count': total_count - selected_count
        })
        
    except Exception as e:
        logger.error(f"Error contando leads por estado: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()


@api_pearl_calls.route('/leads/select-by-status', methods=['POST'])
def select_leads_by_status():
    """
    Selecciona/deselecciona TODOS los leads que coincidan con un estado específico.
    
    Body JSON:
        status_field: Campo de estado (ej: 'status_level_1', 'call_status') 
        status_value: Valor del estado (ej: 'Volver a llamar')
        archivo_origen: Lista de archivos origen para filtrar (opcional)
        selected: boolean - true para seleccionar, false para deseleccionar
    
    Returns:
        JSON: {success: bool, selected_count: int, message: str}
    """
    try:
        data = request.get_json()
        status_field = data.get('status_field', 'status_level_1')
        status_value = data.get('status_value', '')
        archivo_origen = data.get('archivo_origen', [])
        selected = data.get('selected', True)

        # DEBUG: Log de parámetros recibidos
        logger.info(f"[DEBUG] select_leads_by_status - Parámetros recibidos:")
        logger.info(f"[DEBUG]   status_field: {status_field}")
        logger.info(f"[DEBUG]   status_value: {status_value}")
        logger.info(f"[DEBUG]   archivo_origen: {archivo_origen}")
        logger.info(f"[DEBUG]   selected: {selected}")

        if not status_value:
            return jsonify({'error': 'status_value es requerido'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir query para actualizar
        where_conditions = [f"TRIM({status_field}) = %s"]
        where_params = [status_value]

        # CRÍTICO: Solo leads OPEN - NO seleccionar leads cerrados
        where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")

        # TEMPORAL: Incluir leads con estado 'selected' que deberían ser 'no_selected'
        where_conditions.append("(call_status = 'no_selected' OR call_status = 'selected')")
        logger.info(f"[DEBUG] TEMPORAL: Incluyendo leads con call_status 'selected' en selección")

        # CRÍTICO: Excluir leads con cita programada SOLO si no es "Volver a llamar"
        # Si es "Volver a llamar", permitir todas las selecciones independientemente del status_level_2
        if status_value != 'Volver a llamar':
            where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")
        else:
            logger.info(f"[DEBUG] Omitiendo filtro de cita programada para 'Volver a llamar'")

        # Agregar filtro de archivo origen si se especifica
        if archivo_origen:
            # Usar LIKE con TRIM para manejar espacios y variaciones
            archivo_conditions = []
            for archivo in archivo_origen:
                archivo_conditions.append("TRIM(origen_archivo) LIKE %s")
                where_params.append(f"%{archivo}%")

            where_conditions.append(f"({' OR '.join(archivo_conditions)})")

            # DEBUG: Log del filtro de archivo construido
            logger.info(f"[DEBUG] Filtro archivo construido: {' OR '.join(archivo_conditions)}")
            logger.info(f"[DEBUG] Parámetros archivo añadidos: {[f'%{archivo}%' for archivo in archivo_origen]}")

        where_clause = ' AND '.join(where_conditions)

        # Actualizar leads que coincidan
        update_query = f"""
            UPDATE leads
            SET selected_for_calling = %s,
                updated_at = NOW()
            WHERE {where_clause}
        """

        # DEBUG: Log de consulta SQL y parámetros
        final_params = [1 if selected else 0] + where_params
        logger.info(f"[DEBUG] Query SQL completa: {update_query}")
        logger.info(f"[DEBUG] Where clause: {where_clause}")
        logger.info(f"[DEBUG] Parámetros WHERE: {where_params}")
        logger.info(f"[DEBUG] Parámetros finales: {final_params}")

        try:
            cursor.execute(update_query, final_params)
            affected_count = cursor.rowcount
            logger.info(f"[DEBUG] Consulta ejecutada exitosamente, filas afectadas: {affected_count}")
        except Exception as sql_error:
            logger.error(f"[ERROR] Error ejecutando consulta SQL: {sql_error}")
            logger.error(f"[ERROR] Query: {update_query}")
            logger.error(f"[ERROR] Parámetros: {final_params}")
            raise
        
        conn.commit()
        
        action = "seleccionados" if selected else "deseleccionados"
        origenMsg = f" (origen: {', '.join(archivo_origen)})" if archivo_origen else ""
        
        logger.info(f"Leads {action} por estado: {affected_count} con {status_field}={status_value}{origenMsg}")
        
        return jsonify({
            'success': True,
            'selected_count': affected_count,
            'message': f'{affected_count} leads {action} con {status_field}="{status_value}"{origenMsg}'
        })
        
    except Exception as e:
        logger.error(f"Error seleccionando leads por estado: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()


@api_pearl_calls.route('/leads/select-without-status', methods=['POST'])
def select_leads_without_status():
    """
    Selecciona TODOS los leads que NO tienen status_level_1 asignado (aparecen como N/A).
    Solo selecciona leads que están OPEN y sin cita programada.
    
    Body JSON:
        archivo_origen: Lista de archivos origen para filtrar (opcional)
    
    Returns:
        JSON: {success: bool, selected_count: int, message: str}
    """
    try:
        data = request.get_json() or {}
        archivo_origen = data.get('archivo_origen', [])
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir query para seleccionar leads sin estado
        where_conditions = [
            "(status_level_1 IS NULL OR TRIM(status_level_1) = '' OR status_level_1 = 'None')"
        ]
        params = []
        
        # CRÍTICO: Solo leads OPEN - NO seleccionar leads cerrados
        where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")
        
        # CRÍTICO: Excluir leads con cita programada
        where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")
        
        # Agregar filtro de archivo origen si se especifica
        if archivo_origen:
            placeholders = ','.join(['%s'] * len(archivo_origen))
            where_conditions.append(f"origen_archivo IN ({placeholders})")
            params.extend(archivo_origen)
        
        where_clause = ' AND '.join(where_conditions)
        
        # Actualizar leads sin estado que coincidan
        update_query = f"""
            UPDATE leads 
            SET selected_for_calling = TRUE,
                updated_at = NOW()
            WHERE {where_clause}
        """
        
        cursor.execute(update_query, params)
        affected_count = cursor.rowcount
        conn.commit()
        
        origenMsg = f" (origen: {', '.join(archivo_origen)})" if archivo_origen else ""
        logger.info(f"Leads sin estado seleccionados: {affected_count}{origenMsg}")
        
        return jsonify({
            'success': True,
            'selected_count': affected_count,
            'message': f'{affected_count} leads sin estado seleccionados para llamadas{origenMsg}'
        })
        
    except Exception as e:
        logger.error(f"Error seleccionando leads sin estado: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()


@api_pearl_calls.route('/leads/fix-no-interesados', methods=['POST'])
def fix_no_interesados_status():
    """
    Actualiza el lead_status a 'closed' para todos los leads con status_level_1 = 'No Interesado'
    que actualmente tienen lead_status = 'open' o NULL.
    
    Returns:
        JSON: {success: bool, updated_count: int, message: str}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Actualizar leads "No Interesado" que están 'open' o NULL a 'closed'
        update_query = """
            UPDATE leads 
            SET lead_status = 'closed',
                updated_at = NOW()
            WHERE TRIM(status_level_1) = 'No Interesado'
            AND (lead_status IS NULL OR TRIM(lead_status) != 'closed')
        """
        
        cursor.execute(update_query)
        updated_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Se actualizaron {updated_count} leads 'No Interesado' a estado 'closed'")
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Se actualizaron {updated_count} leads "No Interesado" a estado cerrado'
        })
        
    except Exception as e:
        logger.error(f"Error actualizando leads 'No Interesado': {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()


@api_pearl_calls.route('/leads/deselect-all', methods=['POST'])
def deselect_all_leads():
    """
    Deselecciona TODOS los leads en la base de datos, respetando filtros de archivo origen.
    
    Body JSON:
        archivo_origen: Lista de archivos origen para filtrar (opcional)
    
    Returns:
        JSON: {success: bool, deselected_count: int, message: str}
    """
    try:
        data = request.get_json() or {}
        archivo_origen = data.get('archivo_origen', [])
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir query para deseleccionar
        where_conditions = ["1=1"]  # Base condition
        params = []
        
        # Agregar filtro de archivo origen si se especifica
        if archivo_origen:
            placeholders = ','.join(['%s'] * len(archivo_origen))
            where_conditions.append(f"origen_archivo IN ({placeholders})")
            params.extend(archivo_origen)
        
        where_clause = ' AND '.join(where_conditions)
        
        # Actualizar todos los leads que coincidan con los filtros
        update_query = f"""
            UPDATE leads 
            SET selected_for_calling = FALSE,
                updated_at = NOW()
            WHERE {where_clause}
            AND selected_for_calling = TRUE
        """
        
        cursor.execute(update_query, params)
        affected_count = cursor.rowcount
        conn.commit()
        
        origenMsg = f" filtrados por archivo origen: {', '.join(archivo_origen)}" if archivo_origen else ""
        logger.info(f"Leads deseleccionados: {affected_count}{origenMsg}")
        
        return jsonify({
            'success': True,
            'deselected_count': affected_count,
            'message': f'{affected_count} leads deseleccionados{origenMsg}'
        })
        
    except Exception as e:
        logger.error(f"Error deseleccionando todos los leads: {e}")
        return jsonify({'error': str(e)}), 500
        
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()

@api_pearl_calls.route('/leads/fix-selected-status', methods=['POST'])
def fix_selected_status():
    """
    ENDPOINT TEMPORAL: Corregir estados 'selected' incorrectos.
    Convertir todos los call_status = 'selected' a 'no_selected'
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Contar leads con estado 'selected'
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE call_status = 'selected'")
        total_before = cursor.fetchone()['total']

        if total_before == 0:
            return jsonify({
                'success': True,
                'message': 'No hay leads con estado selected para corregir',
                'fixed_count': 0
            })

        # Corregir estados 'selected' a 'no_selected'
        cursor.execute("""
            UPDATE leads
            SET call_status = 'no_selected',
                updated_at = NOW()
            WHERE call_status = 'selected'
        """)

        fixed_count = cursor.rowcount
        conn.commit()

        logger.info(f"Corregidos {fixed_count} leads con estado 'selected' -> 'no_selected'")

        return jsonify({
            'success': True,
            'message': f'Corregidos {fixed_count} leads con estado selected incorrecto',
            'fixed_count': fixed_count,
            'total_before': total_before
        })

    except Exception as e:
        logger.error(f"Error corrigiendo estados selected: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
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

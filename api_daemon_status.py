#!/usr/bin/env python3
"""
API de Estado del Daemon de Reservas Automáticas
===============================================

Endpoints para monitorear el estado del daemon de reservas automáticas
y obtener información sobre su funcionamiento.
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
from daemon_monitor import daemon_monitor

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint
daemon_status_api = Blueprint('daemon_status_api', __name__)

@daemon_status_api.route('/api/daemon/status', methods=['GET'])
def get_daemon_status():
    """
    Obtiene el estado actual del daemon de reservas automáticas
    
    Returns:
        JSON con información detallada del estado del daemon
    """
    try:
        # Obtener estado desde base de datos
        db_status = daemon_monitor.get_status_from_db()
        
        if not db_status:
            return jsonify({
                'success': False,
                'message': 'No se pudo obtener el estado del daemon',
                'status': 'unknown',
                'daemon_running': False
            }), 500
        
        # Verificar si el daemon está saludable
        is_healthy, health_message = daemon_monitor.is_daemon_healthy()
        
        response_data = {
            'success': True,
            'message': health_message,
            'status': 'healthy' if is_healthy else 'unhealthy',
            'daemon_running': db_status.get('is_running', False),
            'daemon_info': {
                'last_heartbeat': db_status.get('last_heartbeat'),
                'last_cycle_start': db_status.get('last_cycle_start'),
                'last_cycle_end': db_status.get('last_cycle_end'),
                'last_cycle_duration': float(db_status.get('last_cycle_duration', 0)) if db_status.get('last_cycle_duration') else None,
                'leads_processed': db_status.get('leads_processed', 0),
                'reservations_successful': db_status.get('reservations_successful', 0),
                'reservations_failed': db_status.get('reservations_failed', 0),
                'error_count': db_status.get('error_count', 0),
                'last_error': db_status.get('last_error'),
                'created_at': db_status.get('created_at'),
                'updated_at': db_status.get('updated_at')
            }
        }
        
        # Si no está saludable, devolver código de error
        status_code = 200 if is_healthy else 503
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del daemon: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'status': 'error',
            'daemon_running': False
        }), 500

@daemon_status_api.route('/api/daemon/healthcheck', methods=['GET'])
def daemon_healthcheck():
    """
    Endpoint simple de healthcheck para monitoreo externo
    
    Returns:
        200 si el daemon está saludable, 503 si no
    """
    try:
        is_healthy, message = daemon_monitor.is_daemon_healthy()
        
        if is_healthy:
            return jsonify({
                'status': 'healthy',
                'message': message,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': message,
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"Error en healthcheck: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error interno: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@daemon_status_api.route('/api/daemon/stats', methods=['GET'])
def get_daemon_stats():
    """
    Obtiene estadísticas resumidas del daemon
    
    Returns:
        JSON con estadísticas del daemon
    """
    try:
        db_status = daemon_monitor.get_status_from_db()
        
        if not db_status:
            return jsonify({
                'success': False,
                'message': 'No se pudieron obtener las estadísticas'
            }), 500
        
        is_healthy, _ = daemon_monitor.is_daemon_healthy()
        
        stats = {
            'success': True,
            'daemon_healthy': is_healthy,
            'daemon_running': db_status.get('is_running', False),
            'stats': {
                'total_leads_processed': db_status.get('leads_processed', 0),
                'successful_reservations': db_status.get('reservations_successful', 0),
                'failed_reservations': db_status.get('reservations_failed', 0),
                'success_rate': 0,
                'error_count': db_status.get('error_count', 0),
                'last_cycle_duration': float(db_status.get('last_cycle_duration', 0)) if db_status.get('last_cycle_duration') else None,
                'uptime_info': {
                    'last_heartbeat': db_status.get('last_heartbeat'),
                    'last_cycle': db_status.get('last_cycle_end'),
                    'daemon_created': db_status.get('created_at')
                }
            }
        }
        
        # Calcular tasa de éxito
        total_reservations = stats['stats']['successful_reservations'] + stats['stats']['failed_reservations']
        if total_reservations > 0:
            stats['stats']['success_rate'] = round(
                (stats['stats']['successful_reservations'] / total_reservations) * 100, 2
            )
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

@daemon_status_api.route('/api/daemon/alert', methods=['GET'])
def check_daemon_alert():
    """
    Verifica si hay alertas del daemon que requieren atención
    
    Returns:
        JSON indicando si hay alertas y su nivel de severidad
    """
    try:
        is_healthy, message = daemon_monitor.is_daemon_healthy()
        db_status = daemon_monitor.get_status_from_db()
        
        alerts = []
        alert_level = 'none'
        
        if not is_healthy:
            alerts.append({
                'type': 'daemon_unhealthy',
                'message': message,
                'severity': 'critical',
                'timestamp': datetime.now().isoformat()
            })
            alert_level = 'critical'
        
        if db_status and db_status.get('error_count', 0) > 0:
            alerts.append({
                'type': 'errors_detected',
                'message': f"Se han detectado {db_status['error_count']} errores",
                'severity': 'warning',
                'last_error': db_status.get('last_error'),
                'timestamp': datetime.now().isoformat()
            })
            if alert_level == 'none':
                alert_level = 'warning'
        
        if db_status and db_status.get('reservations_failed', 0) > 0:
            total_reservations = db_status.get('reservations_successful', 0) + db_status.get('reservations_failed', 0)
            failure_rate = (db_status.get('reservations_failed', 0) / total_reservations) * 100 if total_reservations > 0 else 0
            
            if failure_rate > 50:  # Más del 50% de fallos
                alerts.append({
                    'type': 'high_failure_rate',
                    'message': f"Alta tasa de fallos en reservas: {failure_rate:.1f}%",
                    'severity': 'warning',
                    'timestamp': datetime.now().isoformat()
                })
                if alert_level == 'none':
                    alert_level = 'warning'
        
        return jsonify({
            'success': True,
            'has_alerts': len(alerts) > 0,
            'alert_level': alert_level,
            'alerts': alerts,
            'checked_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error verificando alertas: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

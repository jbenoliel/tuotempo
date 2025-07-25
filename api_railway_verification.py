#!/usr/bin/env python3
"""
API para Verificación de Servicios en Railway
============================================

Proporciona endpoints web para verificar el estado de todos los servicios
desplegados en Railway desde la interfaz de administración.
"""

from flask import Blueprint, jsonify, request
import requests
import logging
import json
import time
from datetime import datetime
import threading

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint
railway_verification_api = Blueprint('railway_verification_api', __name__)

# URLs de los distintos servicios en Railway
import os

# Servicio web principal
WEB_URL = os.getenv('RAILWAY_WEB_URL', "https://web-production-b743.up.railway.app")

# Servicio de APIs de TuoTempo
TUOTEMPO_API_URL = os.getenv('RAILWAY_TUOTEMPO_API_URL', "https://tuotempo-apis-production.up.railway.app")

# Servicio de actualización de llamadas
LLAMADAS_URL = os.getenv('RAILWAY_LLAMADAS_URL', "https://actualizarllamadas-production.up.railway.app")

# URL base para compatibilidad con código existente
BASE_URL = WEB_URL

# Estado global de la verificación
verification_status = {
    'running': False,
    'last_run': None,
    'results': None,
    'progress': 0,
    'current_test': None
}

class RailwayVerifier:
    """Clase para verificar el estado de los servicios en Railway"""
    
    def __init__(self):
        self.web_url = WEB_URL
        self.tuotempo_api_url = TUOTEMPO_API_URL
        self.llamadas_url = LLAMADAS_URL
        self.results = {}
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Establece callback para reportar progreso"""
        self.progress_callback = callback
    
    def update_progress(self, progress, current_test):
        """Actualiza el progreso de la verificación"""
        if self.progress_callback:
            self.progress_callback(progress, current_test)
    
    def verificar_endpoint(self, url, metodo="GET", datos=None, descripcion="", mostrar_respuesta=False):
        """Verifica que un endpoint esté funcionando correctamente"""
        try:
            # Asegurar que la URL comience con http:// o https://
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            
            logger.info(f"Verificando endpoint: {url} [método: {metodo}]")
            
            if metodo == "GET":
                response = requests.get(url, timeout=15)
            elif metodo == "POST":
                response = requests.post(url, json=datos, timeout=15)
            else:
                return {
                    'success': False,
                    'status_code': None,
                    'error': f'Método no soportado: {metodo}',
                    'response_time': 0
                }
            
            result = {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'error': None if response.status_code == 200 else response.text[:200]
            }
            
            if mostrar_respuesta and response.status_code == 200:
                try:
                    result['response_data'] = response.json()
                except Exception as e:
                    logger.error(f"Error al procesar respuesta JSON: {str(e)}")
                    result['response_data'] = response.text[:500]
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'error': str(e),
                'response_time': 0
            }
    
    def verificar_api_completa(self):
        """Verifica todos los endpoints de la API de resultados de llamadas"""
        api_results = {}
        
        # 1. Verificar status de la API web
        self.update_progress(20, "Verificando API Status")
        api_results['api_status'] = self.verificar_endpoint(
            f"{self.web_url}/api/status", 
            descripcion="API Status Web", 
            mostrar_respuesta=True
        )
        
        # 2. Obtener resultados (API TuoTempo)
        self.update_progress(40, "Obteniendo resultados de leads")
        api_results['obtener_resultados'] = self.verificar_endpoint(
            f"{self.tuotempo_api_url}/api/obtener_resultados",
            descripcion="API Obtener Resultados"
        )
        
        # 3. Verificar API de actualización (sin datos reales) - Servicio de Llamadas
        self.update_progress(50, "Verificando API de actualización")
        # Primero verificar si el servicio está disponible con un GET al status
        status_check = self.verificar_endpoint(
            f"{self.llamadas_url}/api/status",
            descripcion="Status del servicio de llamadas"
        )
        
        if status_check['success']:
            # Si el servicio está disponible, probar el endpoint de actualización
            datos_prueba = {
                "telefono": "600000000",  # Teléfono de prueba sin prefijo
                "status_level_1": "No Interesado",
                "status_level_2": "Prueba automatica"
            }
            
            api_results['actualizar_resultado'] = self.verificar_endpoint(
                f"{self.llamadas_url}/api/actualizar_resultado",
                metodo="POST",
                datos=datos_prueba,
                descripcion="API Actualizar Resultado"
            )
        else:
            # Si el servicio no está disponible, marcar como error
            api_results['actualizar_resultado'] = {
                'success': False,
                'status_code': None,
                'error': f'Servicio de llamadas no disponible: {status_check["error"]}',
                'response_time': 0
            }
        
        # 4. Verificar API de centros (API TuoTempo)
        self.update_progress(60, "Verificando API de centros")
        api_results['api_centros'] = self.verificar_endpoint(
            f"{self.tuotempo_api_url}/api/centros",
            descripcion="API Centros"
        )
        
        # 5. Verificar API de reservas (API TuoTempo)
        self.update_progress(70, "Verificando API de reservas")
        api_results['api_reservas'] = self.verificar_endpoint(
            f"{self.tuotempo_api_url}/api/reservar",
            descripcion="API Reservas"
        )
        
        # 6. Verificar API del daemon (Web)
        self.update_progress(80, "Verificando API del daemon")
        api_results['daemon_status'] = self.verificar_endpoint(
            f"{self.web_url}/api/daemon/healthcheck",
            descripcion="Daemon Healthcheck"
        )
        
        return api_results
    
    def verificar_admin_login(self):
        """Verifica que la página de login esté disponible"""
        return self.verificar_endpoint(f"{self.web_url}/login", descripcion="Página de Login")
    
    def ejecutar_verificacion_completa(self):
        """Ejecuta una verificación completa de todos los servicios"""
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'services': {
                'web': self.web_url,
                'tuotempo_api': self.tuotempo_api_url,
                'llamadas_api': self.llamadas_url
            },
            'tests': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'success_rate': 0
            }
        }
        
        # 1. Verificar que la aplicación esté en línea
        self.update_progress(10, "Verificando aplicación principal")
        self.results['tests']['app_main'] = self.verificar_endpoint(
            f"{self.web_url}/", 
            descripcion="Página principal"
        )
        
        # 2. Verificar API completa
        self.update_progress(20, "Verificando APIs")
        api_results = self.verificar_api_completa()
        self.results['tests'].update(api_results)
        
        # 3. Verificar sistema de administración
        self.update_progress(95, "Verificando sistema de administración")
        self.results['tests']['admin_login'] = self.verificar_admin_login()
        
        # Calcular resumen
        self.update_progress(100, "Completando verificación")
        total_tests = len(self.results['tests'])
        passed_tests = sum(1 for test in self.results['tests'].values() if test['success'])
        failed_tests = total_tests - passed_tests
        
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': round((passed_tests / total_tests * 100), 2) if total_tests > 0 else 0,
            'overall_status': 'success' if failed_tests == 0 else 'warning' if passed_tests > failed_tests else 'error'
        }
        
        return self.results

def update_verification_progress(progress, current_test):
    """Actualiza el progreso global de la verificación"""
    global verification_status
    verification_status['progress'] = progress
    verification_status['current_test'] = current_test

def run_verification_async():
    """Ejecuta la verificación de forma asíncrona"""
    global verification_status
    
    try:
        verification_status['running'] = True
        verification_status['progress'] = 0
        verification_status['current_test'] = 'Iniciando verificación...'
        
        verifier = RailwayVerifier()
        verifier.set_progress_callback(update_verification_progress)
        
        results = verifier.ejecutar_verificacion_completa()
        
        verification_status['results'] = results
        verification_status['last_run'] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"Error en verificación asíncrona: {e}")
        verification_status['results'] = {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
    finally:
        verification_status['running'] = False
        verification_status['progress'] = 100
        verification_status['current_test'] = 'Verificación completada'

@railway_verification_api.route('/api/railway/verify', methods=['POST'])
def start_verification():
    """Inicia una verificación completa de los servicios de Railway"""
    global verification_status
    
    if verification_status['running']:
        return jsonify({
            'success': False,
            'message': 'Ya hay una verificación en curso',
            'status': 'running'
        }), 409
    
    # Iniciar verificación en hilo separado
    thread = threading.Thread(target=run_verification_async, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Verificación iniciada',
        'status': 'started'
    }), 202

@railway_verification_api.route('/api/railway/status', methods=['GET'])
def get_verification_status():
    """Obtiene el estado actual de la verificación"""
    global verification_status
    
    return jsonify({
        'success': True,
        'verification_status': verification_status
    })

@railway_verification_api.route('/api/railway/results', methods=['GET'])
def get_verification_results():
    """Obtiene los resultados de la última verificación"""
    global verification_status
    
    if verification_status['results'] is None:
        return jsonify({
            'success': False,
            'message': 'No hay resultados disponibles. Ejecuta una verificación primero.'
        }), 404
    
    return jsonify({
        'success': True,
        'results': verification_status['results']
    })

@railway_verification_api.route('/api/railway/quick-check', methods=['GET'])
def quick_health_check():
    """Realiza una verificación rápida de los servicios principales"""
    verifier = RailwayVerifier()
    
    quick_tests = {
        'app_main': verifier.verificar_endpoint(f"{WEB_URL}/", descripcion="App Principal"),
        'api_status': verifier.verificar_endpoint(f"{WEB_URL}/api/status", descripcion="API Status"),
        'daemon_health': verifier.verificar_endpoint(f"{WEB_URL}/api/daemon/healthcheck", descripcion="Daemon Health"),
        'tuotempo_api': verifier.verificar_endpoint(f"{TUOTEMPO_API_URL}/api/status", descripcion="API TuoTempo"),
        'llamadas_api': verifier.verificar_endpoint(f"{LLAMADAS_URL}/api/status", descripcion="API Llamadas")
    }
    
    passed = sum(1 for test in quick_tests.values() if test['success'])
    total = len(quick_tests)
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'quick_check': {
            'tests': quick_tests,
            'summary': {
                'total_tests': total,
                'passed_tests': passed,
                'failed_tests': total - passed,
                'success_rate': round((passed / total * 100), 2),
                'overall_status': 'success' if passed == total else 'warning' if passed > 0 else 'error'
            }
        }
    })

@railway_verification_api.route('/api/railway/config', methods=['GET'])
def get_verification_config():
    """Obtiene la configuración actual de verificación"""
    return jsonify({
        'success': True,
        'config': {
            'services': {
                'web': WEB_URL,
                'tuotempo_api': TUOTEMPO_API_URL,
                'llamadas_api': LLAMADAS_URL
            },
            'timeout': 15,
            'endpoints_checked': [
                'Aplicación principal (WEB)',
                'API Status (WEB)',
                'API Obtener Resultados (TUOTEMPO API)', 
                'API Actualizar Resultado (LLAMADAS API)',
                'API Centros (TUOTEMPO API)',
                'API Reservas (TUOTEMPO API)',
                'Daemon Healthcheck (WEB)',
                'Sistema de Administración (WEB)'
            ]
        }
    })

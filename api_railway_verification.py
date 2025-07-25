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

# URL base de la aplicación en Railway
import os
BASE_URL = os.getenv('RAILWAY_BASE_URL', "https://web-production-b743.up.railway.app")

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
        self.base_url = BASE_URL
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
                except:
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
        
        # 1. Verificar status de la API
        self.update_progress(20, "Verificando API Status")
        api_results['api_status'] = self.verificar_endpoint(
            f"{self.base_url}/api/status", 
            descripcion="API Status", 
            mostrar_respuesta=True
        )
        
        if not api_results['api_status']['success']:
            return api_results
        
        # 2. Obtener resultados
        self.update_progress(40, "Obteniendo resultados de leads")
        api_results['obtener_resultados'] = self.verificar_endpoint(
            f"{self.base_url}/api/obtener_resultados",
            descripcion="API Obtener Resultados"
        )
        
        # 3. Verificar API de actualización (sin datos reales)
        self.update_progress(60, "Verificando API de actualización")
        datos_prueba = {
            "telefono": "+34600000000",  # Teléfono de prueba
            "no_interesado": True
        }
        
        api_results['actualizar_resultado'] = self.verificar_endpoint(
            f"{self.base_url}/api/actualizar_resultado",
            metodo="POST",
            datos=datos_prueba,
            descripcion="API Actualizar Resultado"
        )
        
        # 4. Verificar API de centros
        self.update_progress(70, "Verificando API de centros")
        api_results['api_centros'] = self.verificar_endpoint(
            f"{self.base_url}/api/centros",
            descripcion="API Centros"
        )
        
        # 5. Verificar API de reservas
        self.update_progress(80, "Verificando API de reservas")
        api_results['api_reservas'] = self.verificar_endpoint(
            f"{self.base_url}/api/reservar",
            descripcion="API Reservas"
        )
        
        # 6. Verificar API del daemon
        self.update_progress(90, "Verificando API del daemon")
        api_results['daemon_status'] = self.verificar_endpoint(
            f"{self.base_url}/api/daemon/healthcheck",
            descripcion="Daemon Healthcheck"
        )
        
        return api_results
    
    def verificar_admin_login(self):
        """Verifica que la página de login esté disponible"""
        return self.verificar_endpoint(f"{self.base_url}/login", descripcion="Página de Login")
    
    def ejecutar_verificacion_completa(self):
        """Ejecuta una verificación completa de todos los servicios"""
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
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
            f"{self.base_url}/", 
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
        'app_main': verifier.verificar_endpoint(f"{BASE_URL}/", descripcion="App Principal"),
        'api_status': verifier.verificar_endpoint(f"{BASE_URL}/api/status", descripcion="API Status"),
        'daemon_health': verifier.verificar_endpoint(f"{BASE_URL}/api/daemon/healthcheck", descripcion="Daemon Health")
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
            'base_url': BASE_URL,
            'timeout': 15,
            'endpoints_checked': [
                'Aplicación principal',
                'API Status',
                'API Obtener Resultados', 
                'API Actualizar Resultado',
                'API Centros',
                'API Reservas',
                'Daemon Healthcheck',
                'Sistema de Administración'
            ]
        }
    })

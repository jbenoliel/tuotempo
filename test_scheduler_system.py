"""
Pruebas completas del sistema de Scheduler integrado.
Testa todas las funcionalidades del scheduler y su integración.
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta

# Añadir directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from call_scheduler import CallScheduler, schedule_failed_call
from call_manager_scheduler_integration import (
    enhanced_process_call_result, 
    integrate_scheduler_with_call_manager,
    get_scheduler_integration_stats
)
from db import get_connection

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchedulerSystemTest:
    def __init__(self):
        self.scheduler = CallScheduler()
        self.test_lead_id = None
        
    def setup_test_data(self):
        """Crea datos de prueba en la BD."""
        conn = get_connection()
        if not conn:
            logger.error("No se pudo conectar a la BD para setup")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Insertar un lead de prueba
                cursor.execute("""
                    INSERT INTO leads (
                        nombre, apellidos, telefono, 
                        lead_status, call_attempts_count,
                        updated_at
                    ) VALUES (
                        'Test', 'Scheduler', '+34666123456',
                        'open', 0,
                        NOW()
                    )
                """)
                
                self.test_lead_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Lead de prueba creado con ID: {self.test_lead_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error creando datos de prueba: {e}")
            return False
        finally:
            conn.close()
    
    def cleanup_test_data(self):
        """Limpia los datos de prueba."""
        if not self.test_lead_id:
            return
        
        conn = get_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cursor:
                # Limpiar call_schedule
                cursor.execute("DELETE FROM call_schedule WHERE lead_id = %s", (self.test_lead_id,))
                
                # Limpiar lead de prueba
                cursor.execute("DELETE FROM leads WHERE id = %s", (self.test_lead_id,))
                
                conn.commit()
                logger.info(f"Datos de prueba eliminados para lead {self.test_lead_id}")
                
        except Exception as e:
            logger.error(f"Error limpiando datos de prueba: {e}")
        finally:
            conn.close()
    
    def test_scheduler_configuration(self):
        """Prueba la carga de configuración del scheduler."""
        print("\n" + "="*50)
        print("TEST 1: Configuración del Scheduler")
        print("="*50)
        
        config = self.scheduler.config
        
        # Verificar configuraciones básicas
        assert 'working_hours_start' in config, "Falta working_hours_start en config"
        assert 'working_hours_end' in config, "Falta working_hours_end en config"
        assert 'reschedule_hours' in config, "Falta reschedule_hours en config"
        assert 'max_attempts' in config, "Falta max_attempts en config"
        
        print("Configuracion cargada correctamente:")
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        # Probar horarios laborales
        working_start, working_end = self.scheduler.get_working_hours()
        print(f"Horarios laborales: {working_start} - {working_end}")
        
        return True
    
    def test_working_hours_logic(self):
        """Prueba la lógica de horarios laborales."""
        print("\n" + "="*50)
        print("TEST 2: Lógica de Horarios Laborales")
        print("="*50)
        
        # Crear fechas de prueba
        # Lunes 10:30 AM (dentro de horario)
        monday_morning = datetime(2023, 1, 2, 10, 30)  # Lunes
        is_working = self.scheduler.is_working_time(monday_morning)
        print(f"Lunes 10:30 AM es horario laboral: {is_working}")
        assert is_working, "Lunes 10:30 AM debería ser horario laboral"
        
        # Sábado 12:00 PM (fuera de horario - fin de semana)
        saturday_noon = datetime(2023, 1, 7, 12, 0)  # Sábado
        is_working = self.scheduler.is_working_time(saturday_noon)
        print(f"Sabado 12:00 PM es horario laboral: {is_working}")
        assert not is_working, "Sábado no debería ser horario laboral"
        
        # Lunes 22:00 PM (fuera de horario - muy tarde)
        monday_night = datetime(2023, 1, 2, 22, 0)  # Lunes
        is_working = self.scheduler.is_working_time(monday_night)
        print(f"Lunes 22:00 PM es horario laboral: {is_working}")
        assert not is_working, "Lunes 22:00 PM debería estar fuera de horario"
        
        # Probar find_next_working_slot
        next_slot = self.scheduler.find_next_working_slot(saturday_noon)
        print(f"Siguiente slot laboral desde sabado: {next_slot}")
        assert next_slot.isoweekday() == 1, "Debería ser lunes"  # Lunes
        
        return True
    
    def test_call_scheduling(self):
        """Prueba la programación de llamadas."""
        print("\n" + "="*50)
        print("TEST 3: Programación de Llamadas")
        print("="*50)
        
        if not self.test_lead_id:
            print("No hay lead de prueba disponible")
            return False
        
        # Probar programación de reintento
        result = self.scheduler.schedule_retry(self.test_lead_id, 'no_answer')
        print(f"Reintento programado: {result}")
        assert result, "Debería haberse programado el reintento"
        
        # Verificar que se creó el registro en call_schedule
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT * FROM call_schedule 
                    WHERE lead_id = %s AND status = 'pending'
                    ORDER BY created_at DESC LIMIT 1
                """, (self.test_lead_id,))
                
                scheduled_call = cursor.fetchone()
                assert scheduled_call, "Debería existir una llamada programada"
                
                print(f"Llamada programada para: {scheduled_call['scheduled_at']}")
                print(f"Numero de intento: {scheduled_call['attempt_number']}")
                print(f"Outcome anterior: {scheduled_call['last_outcome']}")
                
        finally:
            conn.close()
        
        return True
    
    def test_max_attempts_closure(self):
        """Prueba el cierre automático después del máximo de intentos."""
        print("\n" + "="*50)
        print("TEST 4: Cierre Automático (Máximo Intentos)")
        print("="*50)
        
        if not self.test_lead_id:
            print("No hay lead de prueba disponible")
            return False
        
        # Configurar lead con 5 intentos (cerca del máximo)
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE leads 
                    SET call_attempts_count = 5, lead_status = 'open'
                    WHERE id = %s
                """, (self.test_lead_id,))
                conn.commit()
        finally:
            conn.close()
        
        # Intentar programar reintento (debería cerrar el lead)
        result = self.scheduler.schedule_retry(self.test_lead_id, 'no_answer')
        print(f"Resultado programacion (esperado: False para cierre): {result}")
        assert not result, "Debería haber cerrado el lead por máximo intentos"
        
        # Verificar que el lead está cerrado
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT lead_status, closure_reason, call_attempts_count
                    FROM leads WHERE id = %s
                """, (self.test_lead_id,))
                
                lead = cursor.fetchone()
                print(f"Estado final del lead: {lead['lead_status']}")
                print(f"Razon de cierre: {lead['closure_reason']}")
                print(f"Intentos totales: {lead['call_attempts_count']}")
                
                assert lead['lead_status'] == 'closed', "El lead debería estar cerrado"
                assert lead['closure_reason'] is not None, "Debería tener razón de cierre"
                
        finally:
            conn.close()
        
        return True
    
    def test_integration_functions(self):
        """Prueba las funciones de integración."""
        print("\n" + "="*50)
        print("TEST 5: Funciones de Integración")
        print("="*50)
        
        # Probar estadísticas de integración
        stats = get_scheduler_integration_stats()
        print(f"Estadisticas de integracion obtenidas: {stats}")
        assert isinstance(stats, dict), "Las estadísticas deberían ser un dict"
        
        # Probar integración con call manager (sin leads programados)
        scheduled_calls = integrate_scheduler_with_call_manager()
        print(f"Llamadas programadas obtenidas: {len(scheduled_calls)}")
        assert isinstance(scheduled_calls, list), "Debería devolver una lista"
        
        # Probar procesamiento de resultado de llamada
        test_result = {'status': 'failed', 'success': False, 'error_message': 'no answer'}
        if self.test_lead_id:
            # Resetear el lead para la prueba
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE leads 
                        SET call_attempts_count = 0, lead_status = 'open'
                        WHERE id = %s
                    """, (self.test_lead_id,))
                    conn.commit()
            finally:
                conn.close()
            
            # Probar enhanced_process_call_result
            result = enhanced_process_call_result(self.test_lead_id, test_result)
            print(f"Procesamiento de resultado: {result}")
            assert result, "Debería procesar el resultado correctamente"
        
        return True
    
    def test_scheduler_statistics(self):
        """Prueba las estadísticas del scheduler."""
        print("\n" + "="*50)
        print("TEST 6: Estadísticas del Scheduler")
        print("="*50)
        
        stats = self.scheduler.get_statistics()
        print("Estadisticas obtenidas:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        assert isinstance(stats, dict), "Las estadísticas deberían ser un dict"
        
        # Verificar claves esperadas
        expected_keys = ['pending_calls', 'scheduled_today', 'closures', 'avg_attempts', 'max_attempts']
        for key in expected_keys:
            assert key in stats, f"Falta la clave {key} en estadísticas"
        
        return True
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas del sistema."""
        print("INICIANDO PRUEBAS DEL SISTEMA SCHEDULER")
        print("="*60)
        
        # Setup
        if not self.setup_test_data():
            print("Error en setup de datos de prueba")
            return False
        
        try:
            tests = [
                self.test_scheduler_configuration,
                self.test_working_hours_logic,
                self.test_call_scheduling,
                self.test_max_attempts_closure,
                self.test_integration_functions,
                self.test_scheduler_statistics
            ]
            
            passed = 0
            failed = 0
            
            for test in tests:
                try:
                    if test():
                        passed += 1
                        print(f"PASS: {test.__name__}")
                    else:
                        failed += 1
                        print(f"FAIL: {test.__name__}")
                except Exception as e:
                    failed += 1
                    print(f"ERROR: {test.__name__}: {e}")
                    logger.error(f"Error en {test.__name__}: {e}", exc_info=True)
            
            print("\n" + "="*60)
            print("RESULTADOS FINALES:")
            print(f"   Pruebas pasadas: {passed}")
            print(f"   Pruebas fallidas: {failed}")
            print(f"   Total: {passed + failed}")
            
            if failed == 0:
                print("TODAS LAS PRUEBAS PASARON!")
                return True
            else:
                print("Algunas pruebas fallaron. Revisa los logs.")
                return False
                
        finally:
            # Cleanup
            self.cleanup_test_data()

if __name__ == "__main__":
    test_system = SchedulerSystemTest()
    success = test_system.run_all_tests()
    sys.exit(0 if success else 1)
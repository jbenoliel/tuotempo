#!/usr/bin/env python3
"""
Script para probar la corrección del SQL en mark_successful_call
"""
import sys
import os
import logging

# Agregar el directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from call_manager_scheduler_integration import mark_successful_call

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sql_correction():
    """
    Prueba la corrección del SQL con un caso simple
    """
    print("PROBANDO CORRECCION DE SQL PARA mark_successful_call")
    print("="*60)
    
    # Datos de prueba para un lead existente
    lead_id = 2454  # El que ya usamos
    
    # Simular call_result (éxito)
    call_result = {
        'success': True,
        'status': 'completed',
        'duration': 99
    }
    
    # Datos simples de Pearl AI (sin información de cita para probar caso básico)
    pearl_response = {
        "id": "test123",
        "status": 4,
        "collectedInfo": []  # Sin datos de cita para probar solo el caso básico
    }
    
    print(f"Lead ID: {lead_id}")
    print("Caso: Sin información de cita (solo actualización básica)")
    print("\nEjecutando mark_successful_call()...")
    print("-" * 60)
    
    try:
        # Llamar a la función corregida
        result = mark_successful_call(lead_id, call_result, pearl_response)
        
        if result is not False:
            print("✅ Función ejecutada exitosamente - Error SQL corregido")
        else:
            print("❌ Error en la función mark_successful_call")
            
    except Exception as e:
        print(f"❌ Error ejecutando prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sql_correction()
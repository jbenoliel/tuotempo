#!/usr/bin/env python3
"""
Script para probar la corrección de procesamiento de citas para el lead 634307425
"""
import sys
import os
import logging
from datetime import datetime

# Agregar el directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from call_manager_scheduler_integration import mark_successful_call

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mark_successful_call():
    """
    Prueba la función mark_successful_call con los datos reales de Pearl AI 
    para el lead 634307425
    """
    print("PROBANDO CORRECCIÓN PARA LEAD 634307425")
    print("="*60)
    
    # Datos del lead
    lead_id = 2454
    
    # Simular call_result (éxito)
    call_result = {
        'success': True,
        'status': 'completed',
        'duration': 99
    }
    
    # Datos reales de Pearl AI (llamada más reciente)
    pearl_response = {
        "id": "68c30a728a2fc8e5ce034062",
        "startTime": "2025-09-11T17:44:30.502Z",
        "conversationStatus": 100,
        "status": 4,
        "from": "339900",
        "to": "+34634307425",
        "name": "LILIANA ROSSMERY LABRA CORASI",
        "duration": 99,
        "collectedInfo": [
            {
                "id": "agentName",
                "name": "agent name",
                "value": "ana martín"
            },
            {
                "id": "dias_tardes",
                "name": "dias_tardes",
                "value": "Buenas tardes"
            },
            {
                "id": "fechaDeseada",
                "name": "fechaDeseada",
                "value": "25-09-2025"
            },
            {
                "id": "firstName",
                "name": "First Name",
                "value": "LILIANA ROSSMERY"
            },
            {
                "id": "horaDeseada",
                "name": "horaDeseada",
                "value": "17:00:00"
            },
            {
                "id": "interesado",
                "name": "interesado",
                "value": "interesada"
            },
            {
                "id": "lastName",
                "name": "Last Name",
                "value": "LABRA CORASI"
            },
            {
                "id": "phoneNumber",
                "name": "Phone Number",
                "value": "+34634307425"
            },
            {
                "id": "preferenciaMT",
                "name": "preferenciaMT",
                "value": "afternoon"
            },
            {
                "id": "sr_sra",
                "name": "sr_sra",
                "value": "señora"
            }
        ]
    }
    
    print(f"Lead ID: {lead_id}")
    print(f"Fecha esperada: 25-09-2025 -> 2025-09-25")
    print(f"Hora esperada: 17:00:00")
    print(f"Estado esperado: Cita Agendada")
    print("\nEjecutando mark_successful_call()...")
    print("-" * 60)
    
    try:
        # Llamar a la función corregida
        result = mark_successful_call(lead_id, call_result, pearl_response)
        
        if result is not False:
            print("✅ Función ejecutada exitosamente")
            
            # Verificar el resultado en la BD
            import pymysql
            from config import settings
            
            connection = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_DATABASE,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, nombre, apellidos, telefono,
                               cita, hora_cita, status_level_1, resultado_llamada,
                               call_status, updated_at
                        FROM leads 
                        WHERE id = %s
                    """, (lead_id,))
                    
                    lead = cursor.fetchone()
                    
                    if lead:
                        print("\n📋 RESULTADO EN BASE DE DATOS:")
                        print(f"Nombre: {lead['nombre']} {lead['apellidos']}")
                        print(f"Teléfono: {lead['telefono']}")
                        print(f"Cita: {lead['cita']}")
                        print(f"Hora cita: {lead['hora_cita']}")
                        print(f"Status Level 1: {lead['status_level_1']}")
                        print(f"Resultado llamada: {lead['resultado_llamada']}")
                        print(f"Call Status: {lead['call_status']}")
                        print(f"Actualizado: {lead['updated_at']}")
                        
                        # Verificar si se procesó correctamente
                        success = True
                        if lead['cita'] != datetime(2025, 9, 25).date():
                            print("❌ FECHA NO ACTUALIZADA CORRECTAMENTE")
                            success = False
                        if lead['hora_cita'] != datetime.strptime("17:00:00", "%H:%M:%S").time():
                            print("❌ HORA NO ACTUALIZADA CORRECTAMENTE") 
                            success = False
                        if lead['status_level_1'] != 'Cita Agendada':
                            print("❌ STATUS NO ACTUALIZADO CORRECTAMENTE")
                            success = False
                            
                        if success:
                            print("\n🎉 ¡CORRECCIÓN EXITOSA! El lead ahora tiene la cita procesada correctamente.")
                        else:
                            print("\n⚠️ Algunos campos no se actualizaron correctamente.")
                    else:
                        print("❌ No se encontró el lead en la BD")
                        
            finally:
                connection.close()
        else:
            print("❌ Error en la función mark_successful_call")
            
    except Exception as e:
        print(f"❌ Error ejecutando prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mark_successful_call()
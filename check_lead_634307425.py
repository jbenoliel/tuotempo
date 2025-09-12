#!/usr/bin/env python3
import pymysql
from config import settings
import os

def connect_to_db():
    """Conectar a la base de datos"""
    try:
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

def check_lead_634307425():
    """Buscar y mostrar información del lead con teléfono 634307425"""
    connection = connect_to_db()
    if not connection:
        return
    
    try:
        with connection.cursor() as cursor:
            # Buscar el lead por teléfono
            query = """
            SELECT 
                id, nombre, apellidos, telefono, telefono2, email,
                cita, hora_cita, 
                status_level_1, status_level_2, ultimo_estado, resultado_llamada,
                call_status, call_priority, selected_for_calling,
                last_call_attempt, call_attempts_count, call_error_message,
                lead_status, closure_reason,
                updated_at
            FROM leads 
            WHERE telefono = %s OR telefono2 = %s
            """
            
            cursor.execute(query, ('634307425', '634307425'))
            lead = cursor.fetchone()
            
            if not lead:
                print("No se encontró ningún lead con el teléfono 634307425")
                return
            
            print("=== INFORMACIÓN DEL LEAD ===")
            print(f"ID: {lead['id']}")
            print(f"Nombre: {lead['nombre']} {lead['apellidos']}")
            print(f"Teléfono principal: {lead['telefono']}")
            print(f"Teléfono secundario: {lead['telefono2']}")
            print(f"Email: {lead['email']}")
            
            print("\n=== INFORMACIÓN DE CITA ===")
            print(f"Fecha cita: {lead['cita']}")
            print(f"Hora cita: {lead['hora_cita']}")
            
            print("\n=== ESTADOS ===")
            print(f"Status Level 1: {lead['status_level_1']}")
            print(f"Status Level 2: {lead['status_level_2']}")
            print(f"Último estado: {lead['ultimo_estado']}")
            print(f"Resultado llamada: {lead['resultado_llamada']}")
            
            print("\n=== SISTEMA DE LLAMADAS ===")
            print(f"Call Status: {lead['call_status']}")
            print(f"Call Priority: {lead['call_priority']}")
            print(f"Selected for calling: {lead['selected_for_calling']}")
            print(f"Last call attempt: {lead['last_call_attempt']}")
            print(f"Call attempts count: {lead['call_attempts_count']}")
            print(f"Call error message: {lead['call_error_message']}")
            
            print("\n=== ESTADO DEL LEAD ===")
            print(f"Lead Status: {lead['lead_status']}")
            print(f"Closure reason: {lead['closure_reason']}")
            print(f"Updated at: {lead['updated_at']}")
            
            # Buscar llamadas relacionadas en pearl_calls
            print("\n=== LLAMADAS EN PEARL_CALLS ===")
            query_calls = """
            SELECT call_id, phone_number, status, duration, cost, summary, created_at, updated_at
            FROM pearl_calls 
            WHERE phone_number = %s OR lead_id = %s
            ORDER BY created_at DESC
            """
            
            cursor.execute(query_calls, ('634307425', lead['id']))
            calls = cursor.fetchall()
            
            if calls:
                for i, call in enumerate(calls, 1):
                    print(f"\nLlamada {i}:")
                    print(f"  Call ID: {call['call_id']}")
                    print(f"  Teléfono: {call['phone_number']}")
                    print(f"  Estado: {call['status']}")
                    print(f"  Duración: {call['duration']} segundos")
                    print(f"  Costo: {call['cost']}")
                    print(f"  Resumen: {call['summary']}")
                    print(f"  Creada: {call['created_at']}")
                    print(f"  Actualizada: {call['updated_at']}")
            else:
                print("No se encontraron llamadas en pearl_calls para este teléfono")
                
            # Buscar programaciones en call_schedule
            print("\n=== PROGRAMACIONES EN CALL_SCHEDULE ===")
            query_schedule = """
            SELECT id, scheduled_at, attempt_number, status, last_outcome, created_at, updated_at
            FROM call_schedule 
            WHERE lead_id = %s
            ORDER BY scheduled_at DESC
            """
            
            cursor.execute(query_schedule, (lead['id'],))
            schedules = cursor.fetchall()
            
            if schedules:
                for i, schedule in enumerate(schedules, 1):
                    print(f"\nProgramación {i}:")
                    print(f"  ID: {schedule['id']}")
                    print(f"  Programado para: {schedule['scheduled_at']}")
                    print(f"  Número de intento: {schedule['attempt_number']}")
                    print(f"  Estado: {schedule['status']}")
                    print(f"  Último resultado: {schedule['last_outcome']}")
                    print(f"  Creado: {schedule['created_at']}")
                    print(f"  Actualizado: {schedule['updated_at']}")
            else:
                print("No se encontraron programaciones en call_schedule para este lead")
            
    except Exception as e:
        print(f"Error consultando la base de datos: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    check_lead_634307425()
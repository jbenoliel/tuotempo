#!/usr/bin/env python3
import pymysql
import json
from config import settings

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

def examinar_json_pearl():
    """Examinar toda la información JSON guardada para el teléfono 634307425"""
    connection = connect_to_db()
    if not connection:
        return
    
    try:
        with connection.cursor() as cursor:
            print("=== EXAMINANDO INFORMACIÓN JSON DE PEARL AI ===\n")
            
            # 1. Buscar en la tabla leads - campo pearl_call_response
            print("1. INFORMACIÓN JSON EN TABLA LEADS:")
            cursor.execute("""
                SELECT id, nombre, apellidos, telefono, pearl_call_response
                FROM leads 
                WHERE telefono = %s OR telefono2 = %s
            """, ('634307425', '634307425'))
            
            lead = cursor.fetchone()
            if lead and lead['pearl_call_response']:
                print(f"Lead ID: {lead['id']} - {lead['nombre']} {lead['apellidos']}")
                print("Pearl Call Response JSON:")
                try:
                    json_data = json.loads(lead['pearl_call_response'])
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
                except:
                    print("No es JSON válido:", lead['pearl_call_response'])
            else:
                print("No hay pearl_call_response en la tabla leads")
            
            print("\n" + "="*60 + "\n")
            
            # 2. Buscar en tabla pearl_calls - campos summary, transcription, collected_info
            print("2. INFORMACIÓN JSON EN TABLA PEARL_CALLS:")
            cursor.execute("""
                SELECT call_id, phone_number, status, duration, 
                       summary, transcription, collected_info, recording_url,
                       created_at, updated_at
                FROM pearl_calls 
                WHERE phone_number = %s OR phone_number = %s
                ORDER BY created_at DESC
            """, ('+34634307425', '634307425'))
            
            calls = cursor.fetchall()
            
            for i, call in enumerate(calls, 1):
                print(f"\n--- LLAMADA {i} ---")
                print(f"Call ID: {call['call_id']}")
                print(f"Teléfono: {call['phone_number']}")
                print(f"Estado: {call['status']}")
                print(f"Duración: {call['duration']} segundos")
                print(f"Fecha: {call['created_at']}")
                
                print("\nSUMMARY:")
                if call['summary']:
                    print(call['summary'])
                else:
                    print("(Vacío)")
                
                print("\nTRANSCRIPTION:")
                if call['transcription']:
                    # Si es muy largo, mostrar solo el inicio
                    transcription = call['transcription']
                    if len(transcription) > 1000:
                        print(transcription[:1000] + "... (TRUNCADO)")
                    else:
                        print(transcription)
                else:
                    print("(Vacío)")
                
                print("\nCOLLECTED_INFO (JSON):")
                if call['collected_info']:
                    try:
                        collected_data = json.loads(call['collected_info'])
                        print(json.dumps(collected_data, indent=2, ensure_ascii=False))
                    except:
                        print("No es JSON válido:", call['collected_info'])
                else:
                    print("(Vacío)")
                
                print(f"\nRECORDING URL: {call['recording_url'] or '(Vacío)'}")
            
            if not calls:
                print("No se encontraron llamadas en pearl_calls")
            
            print("\n" + "="*60 + "\n")
            
            # 3. Buscar otros campos JSON que puedan existir
            print("3. OTROS CAMPOS QUE PUEDEN CONTENER INFORMACIÓN:")
            cursor.execute("""
                SELECT id, call_summary, call_notes, call_error_message
                FROM leads 
                WHERE telefono = %s OR telefono2 = %s
            """, ('634307425', '634307425'))
            
            lead_extra = cursor.fetchone()
            if lead_extra:
                print(f"CALL_SUMMARY: {lead_extra['call_summary'] or '(Vacío)'}")
                print(f"CALL_NOTES: {lead_extra['call_notes'] or '(Vacío)'}")
                print(f"CALL_ERROR_MESSAGE: {lead_extra['call_error_message'] or '(Vacío)'}")
            
            # 4. Verificar si hay información de cita que ya está guardada
            print("\n4. INFORMACIÓN DE CITA ACTUAL:")
            cursor.execute("""
                SELECT cita, hora_cita, status_level_1, status_level_2, ultimo_estado, resultado_llamada
                FROM leads 
                WHERE telefono = %s OR telefono2 = %s
            """, ('634307425', '634307425'))
            
            cita_info = cursor.fetchone()
            if cita_info:
                print(f"Cita: {cita_info['cita'] or '(Sin cita)'}")
                print(f"Hora cita: {cita_info['hora_cita'] or '(Sin hora)'}")
                print(f"Status Level 1: {cita_info['status_level_1'] or '(Vacío)'}")
                print(f"Status Level 2: {cita_info['status_level_2'] or '(Vacío)'}")
                print(f"Último estado: {cita_info['ultimo_estado'] or '(Vacío)'}")
                print(f"Resultado llamada: {cita_info['resultado_llamada'] or '(Vacío)'}")
            
    except Exception as e:
        print(f"Error consultando la base de datos: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    examinar_json_pearl()
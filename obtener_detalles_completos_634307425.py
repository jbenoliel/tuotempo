#!/usr/bin/env python3
import pymysql
import json
from config import settings
from pearl_caller import get_pearl_client

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

def obtener_detalles_completos():
    """Obtener detalles completos de Pearl AI para las llamadas del teléfono 634307425"""
    connection = connect_to_db()
    if not connection:
        return
    
    try:
        # Obtener los call_id de las llamadas en la BD
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT call_id, phone_number, status, duration, created_at
                FROM pearl_calls 
                WHERE phone_number = %s OR phone_number = %s
                ORDER BY created_at DESC
            """, ('+34634307425', '634307425'))
            
            calls_in_db = cursor.fetchall()
        
        if not calls_in_db:
            print("No se encontraron llamadas en la base de datos")
            return
        
        # Obtener cliente de Pearl AI
        try:
            pearl_client = get_pearl_client()
            print("Cliente Pearl AI inicializado correctamente")
        except Exception as e:
            print(f"Error inicializando cliente Pearl AI: {e}")
            return
        
        print(f"Encontradas {len(calls_in_db)} llamadas en la BD. Obteniendo detalles completos...")
        print("="*80)
        
        for i, call in enumerate(calls_in_db, 1):
            call_id = call['call_id']
            print(f"\nLLAMADA {i} - ID: {call_id}")
            print(f"Telefono: {call['phone_number']}")
            print(f"Estado en BD: {call['status']}")
            print(f"Duracion: {call['duration']} segundos")
            print(f"Fecha: {call['created_at']}")
            
            try:
                # Obtener detalles completos de Pearl AI
                print(f"\nObteniendo detalles completos de Pearl AI...")
                call_details = pearl_client.get_call_status(call_id)
                
                if call_details:
                    print("Detalles obtenidos exitosamente")
                    print("\nINFORMACION COMPLETA DE PEARL AI:")
                    print(json.dumps(call_details, indent=2, ensure_ascii=False))
                    
                    # Verificar campos específicos importantes
                    print("\nCAMPOS CLAVE PARA CITAS:")
                    print(f"Summary: {call_details.get('summary', 'N/A')}")
                    print(f"Transcription: {call_details.get('transcription', 'N/A')}")
                    print(f"Recording URL: {call_details.get('recording', call_details.get('recordingUrl', 'N/A'))}")
                    print(f"Call Data: {call_details.get('callData', 'N/A')}")
                    print(f"Conversation Status: {call_details.get('conversationStatus', 'N/A')}")
                    print(f"Status: {call_details.get('status', 'N/A')}")
                    print(f"End Time: {call_details.get('endTime', 'N/A')}")
                    
                    # Si hay summary, analizar su contenido
                    summary = call_details.get('summary')
                    if summary and summary.strip():
                        print(f"\nANALISIS DEL SUMMARY:")
                        summary_text = summary.lower()
                        
                        # Buscar palabras clave de cita
                        cita_keywords = ['cita', 'appointment', 'agendar', 'schedule', 'fecha', 'día', 'hora', 'tiempo']
                        rechaza_keywords = ['no interesa', 'no quiere', 'rechaza', 'decline', 'not interested']
                        
                        found_cita = any(keyword in summary_text for keyword in cita_keywords)
                        found_rechaza = any(keyword in summary_text for keyword in rechaza_keywords)
                        
                        print(f"Contiene palabras de CITA: {found_cita}")
                        print(f"Contiene palabras de RECHAZO: {found_rechaza}")
                        
                        if found_cita and not found_rechaza:
                            print("POSIBLE CITA AGENDADA - DEBERIA PROCESARSE!")
                        elif found_rechaza:
                            print("RECHAZO DETECTADO")
                        else:
                            print("RESULTADO AMBIGUO - REVISAR MANUALMENTE")
                    
                else:
                    print("No se pudieron obtener detalles de Pearl AI")
                    
            except Exception as e:
                print(f"Error obteniendo detalles para llamada {call_id}: {e}")
            
            print("-" * 60)
        
    except Exception as e:
        print(f"Error en el proceso: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    print("OBTENIENDO DETALLES COMPLETOS DE PEARL AI PARA 634307425")
    print("="*80)
    obtener_detalles_completos()
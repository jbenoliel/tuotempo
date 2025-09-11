"""
Investigar el contenido real del callData para entender su estructura
"""

import mysql.connector
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def investigar_calldata():
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Obtener una muestra de callData de los últimos 3 días
        cursor.execute("""
            SELECT 
                pc.call_id,
                pc.phone_number,
                pc.call_time,
                pc.collected_info,
                l.nombre,
                l.apellidos,
                l.status_level_1
            FROM pearl_calls pc
            LEFT JOIN leads l ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
            WHERE pc.collected_info IS NOT NULL 
            AND pc.collected_info != ''
            AND pc.collected_info != '{}'
            AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            ORDER BY pc.call_time DESC
            LIMIT 20
        """)
        
        calls = cursor.fetchall()
        
        print("ANALISIS DE CALLDATA - MUESTRA DE 20 LLAMADAS")
        print("="*70)
        
        for i, call in enumerate(calls, 1):
            try:
                call_data = json.loads(call['collected_info'])
                
                print(f"\n{i}. Call {call['call_id']} - {call.get('nombre', 'N/A')} {call.get('apellidos', 'N/A')}")
                print(f"   Tel: {call['phone_number']}")
                print(f"   Status: {call.get('status_level_1', 'N/A')}")
                print(f"   Fecha: {call['call_time']}")
                print(f"   CallData keys: {list(call_data.keys())}")
                
                # Buscar campos de interés
                campos_interes = ['fechaDeseada', 'preferenciaMT', 'callResult', 'firstName', 'lastName']
                for campo in campos_interes:
                    if campo in call_data:
                        print(f"   ► {campo}: {call_data[campo]}")
                
                # Mostrar todo el callData si es pequeño
                if len(str(call_data)) < 500:
                    print(f"   CallData completo: {json.dumps(call_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"   CallData muy grande ({len(str(call_data))} chars)")
                    
            except json.JSONDecodeError as e:
                print(f"   ERROR: JSON inválido - {e}")
            except Exception as e:
                print(f"   ERROR: {e}")
        
        # Buscar específicamente llamadas que contengan texto relacionado con citas
        print(f"\n" + "="*70)
        print("BUSQUEDA DE PATTERNS DE CITA EN CALLDATA")
        print("="*70)
        
        cursor.execute("""
            SELECT 
                pc.call_id,
                pc.phone_number,
                pc.collected_info,
                l.nombre,
                l.apellidos
            FROM pearl_calls pc
            LEFT JOIN leads l ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
            WHERE pc.collected_info IS NOT NULL 
            AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            AND (
                pc.collected_info LIKE '%cita%' 
                OR pc.collected_info LIKE '%fecha%'
                OR pc.collected_info LIKE '%morning%'
                OR pc.collected_info LIKE '%afternoon%'
                OR pc.collected_info LIKE '%agendada%'
                OR pc.collected_info LIKE '%confirmada%'
            )
            LIMIT 10
        """)
        
        cita_calls = cursor.fetchall()
        
        if cita_calls:
            print(f"Encontradas {len(cita_calls)} llamadas con patterns de cita:")
            for call in cita_calls:
                try:
                    call_data = json.loads(call['collected_info'])
                    print(f"\nCall {call['call_id']} - {call.get('nombre', 'N/A')} {call.get('apellidos', 'N/A')}")
                    print(f"CallData: {json.dumps(call_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"Call {call['call_id']}: Error parseando JSON")
        else:
            print("No se encontraron llamadas con patterns de cita")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    investigar_calldata()
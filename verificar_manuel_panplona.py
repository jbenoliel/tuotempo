"""
Verificar si MANUEL PANPLONA NAVARRO se actualizo correctamente
"""

import mysql.connector

def verificar_manuel_panplona():
    conn = mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar MANUEL PANPLONA NAVARRO
        cursor.execute("""
            SELECT 
                id, nombre, apellidos, telefono, 
                status_level_1, status_level_2, 
                updated_at, last_call_attempt
            FROM leads 
            WHERE telefono = '613750493' 
            OR (nombre LIKE '%MANUEL%' AND apellidos LIKE '%PANPLONA%')
            ORDER BY updated_at DESC
        """)
        
        results = cursor.fetchall()
        
        print("VERIFICACION DE MANUEL PANPLONA NAVARRO")
        print("="*50)
        
        if results:
            for lead in results:
                print(f"ID: {lead['id']}")
                print(f"Nombre: {lead.get('nombre', 'N/A')} {lead.get('apellidos', 'N/A')}")
                print(f"Telefono: {lead.get('telefono', 'N/A')}")
                print(f"Status L1: {lead.get('status_level_1', 'N/A')}")
                print(f"Status L2: {lead.get('status_level_2', 'N/A')}")
                print(f"Actualizado: {lead.get('updated_at', 'N/A')}")
                print(f"Ultima llamada: {lead.get('last_call_attempt', 'N/A')}")
                print()
                
                # Verificar si se actualizo correctamente
                if lead.get('status_level_1') == 'Cita Agendada' and lead.get('status_level_2') == 'Con Pack':
                    print("SUCCESS - El fix funciono correctamente!")
                else:
                    print("PROBLEMA - El fix no funciono como esperado")
                    print(f"Esperado: status_level_1='Cita Agendada', status_level_2='Con Pack'")
                    print(f"Actual: status_level_1='{lead.get('status_level_1')}', status_level_2='{lead.get('status_level_2')}'")
        else:
            print("No se encontro el lead MANUEL PANPLONA NAVARRO")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verificar_manuel_panplona()
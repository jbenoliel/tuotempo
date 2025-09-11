"""
Buscar leads que pidieron cita segun Pearl AI
"""

import mysql.connector
import pandas as pd
from datetime import datetime

def get_railway_connection():
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def buscar_leads_cita():
    conn = get_railway_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Lista de nombres de Pearl AI
        nombres = [
            ("YENDERSON", "CHIRINOS"),
            ("MANUEL", "PANPLONA"), 
            ("JOSEFA", "DIVOLS"),
            ("JAUME", "ROBLES"),
            ("MARYLIN", "ROMAIN"),
            ("DARISELA", "CANARIO"),
            ("FELIX", "LOPEZ"),
            ("LUIS", "VALENCIANO"),
            ("KATIA", "PEREZ")
        ]
        
        print("BUSQUEDA DE LEADS QUE PIDIERON CITA")
        print("="*60)
        
        resultados = []
        
        for nombre, apellido in nombres:
            print(f"\nBuscando: {nombre} {apellido}")
            
            cursor.execute("""
                SELECT 
                    id, nombre, apellidos, telefono, nombre_clinica,
                    status_level_1, status_level_2, call_status,
                    updated_at, last_call_attempt
                FROM leads 
                WHERE UPPER(nombre) LIKE %s 
                AND UPPER(apellidos) LIKE %s
                ORDER BY updated_at DESC
                LIMIT 2
            """, (f"%{nombre}%", f"%{apellido}%"))
            
            results = cursor.fetchall()
            
            if results:
                for lead in results:
                    nombre_completo = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}".strip()
                    print(f"  ID {lead['id']}: {nombre_completo}")
                    print(f"    Tel: {lead.get('telefono', 'N/A')}")
                    print(f"    Status L1: {lead.get('status_level_1', 'N/A')}")
                    print(f"    Status L2: {lead.get('status_level_2', 'N/A')}")
                    print(f"    Call Status: {lead.get('call_status', 'N/A')}")
                    print(f"    Actualizado: {lead.get('updated_at', 'N/A')}")
                    
                    resultados.append({
                        'Buscado': f"{nombre} {apellido}",
                        'ID': lead['id'],
                        'Nombre_BD': nombre_completo,
                        'Telefono': lead.get('telefono', 'N/A'),
                        'Status_L1': lead.get('status_level_1', 'N/A'),
                        'Status_L2': lead.get('status_level_2', 'N/A'),
                        'Call_Status': lead.get('call_status', 'N/A'),
                        'Actualizado': lead.get('updated_at', 'N/A')
                    })
            else:
                print(f"  NO ENCONTRADO")
                resultados.append({
                    'Buscado': f"{nombre} {apellido}",
                    'ID': 'NO ENCONTRADO',
                    'Nombre_BD': '',
                    'Telefono': '',
                    'Status_L1': '',
                    'Status_L2': '',
                    'Call_Status': '',
                    'Actualizado': ''
                })
        
        # Generar Excel con resultados
        if resultados:
            df = pd.DataFrame(resultados)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"verificacion_leads_pearl_{timestamp}.xlsx"
            
            df.to_excel(filename, index=False)
            print(f"\nArchivo generado: {filename}")
            print(f"Total leads verificados: {len(resultados)}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    buscar_leads_cita()
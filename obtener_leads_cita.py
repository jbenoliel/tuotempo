"""
Obtener leads con cita agendada
"""

import mysql.connector
import pandas as pd
from datetime import datetime
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

def obtener_leads_cita():
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar leads con "Cita Agendada"
        cursor.execute("""
            SELECT * FROM leads 
            WHERE status_level_1 = 'Cita Agendada'
            ORDER BY updated_at DESC
        """)
        
        leads_cita = cursor.fetchall()
        
        print(f"LEADS CON CITA AGENDADA: {len(leads_cita)}")
        print("="*60)
        
        for lead in leads_cita:
            print(f"\nID: {lead['id']} - {lead.get('nombre', 'N/A')} {lead.get('apellidos', 'N/A')}")
            print(f"  Telefono: {lead.get('telefono', 'N/A')}")
            print(f"  Ciudad: {lead.get('ciudad', 'N/A')}")
            print(f"  Email: {lead.get('email', 'N/A')}")
            print(f"  Clinica: {lead.get('nombre_clinica', 'N/A')}")
            print(f"  Status L1: {lead.get('status_level_1', 'N/A')}")
            print(f"  Status L2: {lead.get('status_level_2', 'N/A')}")
            print(f"  Actualizado: {lead.get('updated_at', 'N/A')}")
            print(f"  Ultima llamada: {lead.get('last_call_attempt', 'N/A')}")
        
        # Exportar a Excel
        if leads_cita:
            df = pd.DataFrame(leads_cita)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_cita_agendada_{timestamp}.xlsx"
            
            df.to_excel(filename, index=False, sheet_name='Citas_Agendadas')
            print(f"\nArchivo generado: {filename}")
            print(f"Total leads con cita: {len(leads_cita)}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    obtener_leads_cita()
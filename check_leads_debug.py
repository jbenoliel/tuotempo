#!/usr/bin/env python3
"""
Script rápido para verificar el estado de la tabla leads
"""

from db import get_connection
import json

def check_leads_table():
    """Verifica el estado de la tabla leads"""
    try:
        print("🔍 Verificando tabla leads...")
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Contar total de leads
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()['total']
        print(f"📊 Total de leads en BD: {total}")
        
        if total == 0:
            print("❌ La tabla leads está vacía!")
            return
        
        # Verificar estructura de campos importantes
        cursor.execute("SHOW COLUMNS FROM leads")
        columns = cursor.fetchall()
        print(f"📋 Columnas en tabla leads: {len(columns)}")
        
        # Verificar si las columnas críticas existen
        critical_columns = ['telefono', 'telefono2', 'call_status', 'selected_for_calling']
        existing_columns = [col['Field'] for col in columns]
        
        for col in critical_columns:
            if col in existing_columns:
                print(f"✅ Columna '{col}' existe")
            else:
                print(f"❌ Columna '{col}' NO existe")
        
        # Mostrar algunos leads de ejemplo
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, telefono2, ciudad, 
                   call_status, selected_for_calling 
            FROM leads 
            LIMIT 5
        """)
        sample_leads = cursor.fetchall()
        
        print(f"\n📋 Muestra de leads (primeros 5):")
        for lead in sample_leads:
            print(f"  ID: {lead['id']}, Nombre: {lead.get('nombre', 'N/A')}, Tel: {lead.get('telefono', 'N/A')}, Status: {lead.get('call_status', 'N/A')}")
        
        # Verificar leads con teléfono válido (condición del endpoint)
        cursor.execute("""
            SELECT COUNT(*) as count_with_phone 
            FROM leads 
            WHERE (telefono IS NOT NULL AND telefono != '') 
               OR (telefono2 IS NOT NULL AND telefono2 != '')
        """)
        with_phone = cursor.fetchone()['count_with_phone']
        print(f"📞 Leads con teléfono válido: {with_phone}")
        
        # Verificar leads seleccionados
        if 'selected_for_calling' in existing_columns:
            cursor.execute("""
                SELECT COUNT(*) as selected_count 
                FROM leads 
                WHERE selected_for_calling = TRUE
            """)
            selected = cursor.fetchone()['selected_count']
            print(f"✅ Leads seleccionados para llamar: {selected}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_api_leads_endpoint():
    """Prueba el endpoint de leads directamente"""
    try:
        import requests
        
        print("\n🌐 Probando endpoint /api/calls/leads...")
        
        response = requests.get("http://localhost:5000/api/calls/leads", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response:")
            print(f"  Success: {data.get('success')}")
            print(f"  Total leads: {len(data.get('leads', []))}")
            print(f"  Pagination: {data.get('pagination')}")
            
            if data.get('leads'):
                print(f"  Primer lead: {data['leads'][0]}")
        else:
            print(f"❌ Error en API: {response.text}")
            
    except Exception as e:
        print(f"❌ Error probando API: {e}")

if __name__ == "__main__":
    check_leads_table()
    test_api_leads_endpoint()

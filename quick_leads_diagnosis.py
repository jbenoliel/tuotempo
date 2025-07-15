#!/usr/bin/env python3
"""
Script simplificado para diagnosticar el problema de leads
"""

def quick_leads_check():
    print("🔍 === DIAGNÓSTICO RÁPIDO DE LEADS ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Contar total de leads
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()['total']
        print(f"📊 Total de leads en BD: {total}")
        
        if total == 0:
            print("❌ PROBLEMA: La tabla leads está vacía!")
            print("💡 Solución: Necesitas cargar datos en la tabla leads")
            return False
        
        # 2. Verificar campos críticos
        cursor.execute("SHOW COLUMNS FROM leads")
        columns = cursor.fetchall()
        column_names = [col['Field'] for col in columns]
        
        critical_fields = [
            'telefono', 'telefono2', 'call_status', 
            'selected_for_calling', 'call_priority'
        ]
        
        missing_fields = []
        for field in critical_fields:
            if field not in column_names:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ PROBLEMA: Campos faltantes en tabla leads: {missing_fields}")
            print("💡 Solución: Necesitas ejecutar las migraciones de BD")
            return False
        
        # 3. Verificar leads con teléfono válido
        cursor.execute("""
            SELECT COUNT(*) as count_with_phone 
            FROM leads 
            WHERE (telefono IS NOT NULL AND telefono != '') 
               OR (telefono2 IS NOT NULL AND telefono2 != '')
        """)
        with_phone = cursor.fetchone()['count_with_phone']
        print(f"📞 Leads con teléfono válido: {with_phone}")
        
        if with_phone == 0:
            print("❌ PROBLEMA: No hay leads con teléfonos válidos!")
            print("💡 La API filtra leads que no tienen teléfono")
            return False
        
        # 4. Mostrar algunos ejemplos
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, ciudad 
            FROM leads 
            WHERE (telefono IS NOT NULL AND telefono != '')
            LIMIT 3
        """)
        examples = cursor.fetchall()
        
        print(f"\n📋 Ejemplos de leads válidos:")
        for lead in examples:
            print(f"  ID: {lead['id']}, Nombre: {lead.get('nombre', 'N/A')}, Tel: {lead.get('telefono', 'N/A')}")
        
        print("✅ La tabla leads parece estar bien configurada")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_leads_api():
    print("\n🌐 === PROBANDO API DE LEADS ===")
    
    try:
        import requests
        
        url = "http://localhost:5000/api/calls/leads"
        print(f"Probando: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API funciona correctamente")
            print(f"  Success: {data.get('success')}")
            print(f"  Total leads devueltos: {len(data.get('leads', []))}")
            
            pagination = data.get('pagination', {})
            print(f"  Total en BD (según API): {pagination.get('total', 0)}")
            
            if len(data.get('leads', [])) == 0:
                print("❌ PROBLEMA: La API no devuelve leads")
                print("💡 Puede ser un problema de filtros o campos faltantes")
                return False
            else:
                print("✅ La API devuelve leads correctamente")
                return True
                
        else:
            print(f"❌ Error en API: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    db_ok = quick_leads_check()
    
    if db_ok:
        api_ok = test_leads_api()
        
        if not api_ok:
            print("\n🔧 POSIBLES SOLUCIONES:")
            print("1. Verifica que las columnas call_status, call_priority, selected_for_calling existan")
            print("2. Ejecuta: python db_schema_manager.py")
            print("3. Reinicia el servidor Flask")
    else:
        print("\n🔧 SOLUCIONES:")
        print("1. Si la tabla está vacía: carga datos desde Excel")
        print("2. Si faltan campos: ejecuta migraciones de BD")
        print("3. Verifica que los teléfonos no estén vacíos")

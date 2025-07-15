#!/usr/bin/env python3
"""
Script para corregir problemas comunes con la tabla leads y el sistema de llamadas
"""

def fix_leads_table():
    print("🔧 === ARREGLANDO TABLA LEADS ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Verificar si hay datos
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()['total']
        print(f"📊 Total de leads en BD: {total}")
        
        if total == 0:
            print("❌ La tabla está vacía. Necesitas cargar datos primero.")
            return False
        
        # 2. Verificar y corregir campos de llamadas
        print("🔧 Verificando campos de llamadas...")
        
        # Asegurar que los campos de llamadas tengan valores por defecto
        fixes = [
            "UPDATE leads SET call_status = 'no_selected' WHERE call_status IS NULL",
            "UPDATE leads SET call_priority = 3 WHERE call_priority IS NULL", 
            "UPDATE leads SET selected_for_calling = FALSE WHERE selected_for_calling IS NULL",
            "UPDATE leads SET call_attempts_count = 0 WHERE call_attempts_count IS NULL"
        ]
        
        for fix in fixes:
            cursor.execute(fix)
            if cursor.rowcount > 0:
                print(f"  ✅ Corregidos {cursor.rowcount} registros")
        
        # 3. Verificar leads con teléfonos válidos
        cursor.execute("""
            SELECT COUNT(*) as count_with_phone 
            FROM leads 
            WHERE (telefono IS NOT NULL AND telefono != '' AND telefono != '0') 
               OR (telefono2 IS NOT NULL AND telefono2 != '' AND telefono2 != '0')
        """)
        with_phone = cursor.fetchone()['count_with_phone']
        print(f"📞 Leads con teléfono válido: {with_phone}")
        
        # 4. Marcar algunos leads como seleccionados para prueba
        if with_phone > 0:
            cursor.execute("""
                UPDATE leads 
                SET selected_for_calling = TRUE, call_status = 'selected'
                WHERE (telefono IS NOT NULL AND telefono != '' AND telefono != '0')
                   OR (telefono2 IS NOT NULL AND telefono2 != '' AND telefono2 != '0')
                LIMIT 10
            """)
            selected_count = cursor.rowcount
            print(f"✅ Marcados {selected_count} leads como seleccionados para prueba")
        
        # 5. Mostrar estadísticas finales
        cursor.execute("""
            SELECT 
                call_status, 
                COUNT(*) as count 
            FROM leads 
            GROUP BY call_status
        """)
        status_stats = cursor.fetchall()
        
        print("📊 Estadísticas por estado:")
        for stat in status_stats:
            print(f"  {stat['call_status']}: {stat['count']}")
        
        conn.commit()
        print("✅ Correcciones aplicadas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_api_after_fix():
    print("\n🌐 === PROBANDO API DESPUÉS DE CORRECCIONES ===")
    
    try:
        import requests
        
        # Probar endpoint básico
        response = requests.get("http://localhost:5000/api/calls/leads", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            leads = data.get('leads', [])
            total = data.get('pagination', {}).get('total', 0)
            
            print(f"✅ API Response:")
            print(f"  Total leads: {total}")
            print(f"  Leads devueltos: {len(leads)}")
            
            if len(leads) > 0:
                print(f"  Primer lead: {leads[0].get('nombre', 'N/A')} - {leads[0].get('telefono', 'N/A')}")
                return True
            else:
                print("❌ Aún no se devuelven leads")
                return False
        else:
            print(f"❌ Error API: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_sample_leads():
    """Crea algunos leads de prueba si la tabla está vacía"""
    print("\n🧪 === CREANDO LEADS DE PRUEBA ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar si ya hay datos
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Ya hay {count} leads en la tabla. No se crearán leads de prueba.")
            return True
        
        # Crear leads de prueba
        sample_leads = [
            ("Juan", "Pérez", "629203315", "Madrid", "Clínica Dental Madrid"),
            ("María", "González", "629203316", "Barcelona", "Dental Barcelona"),
            ("Carlos", "López", "629203317", "Valencia", "Odonto Valencia"),
            ("Ana", "Martín", "629203318", "Sevilla", "Dental Sevilla"),
            ("Pedro", "Ruiz", "629203319", "Bilbao", "Clínica Bilbao")
        ]
        
        for nombre, apellidos, telefono, ciudad, clinica in sample_leads:
            cursor.execute("""
                INSERT INTO leads (
                    nombre, apellidos, telefono, ciudad, nombre_clinica,
                    call_status, call_priority, selected_for_calling, call_attempts_count
                ) VALUES (%s, %s, %s, %s, %s, 'no_selected', 3, FALSE, 0)
            """, (nombre, apellidos, telefono, ciudad, clinica))
        
        conn.commit()
        print(f"✅ Creados {len(sample_leads)} leads de prueba")
        return True
        
    except Exception as e:
        print(f"❌ Error creando leads de prueba: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 HERRAMIENTA DE REPARACIÓN DE LEADS")
    print("Esta herramienta corrige problemas comunes con la tabla leads\n")
    
    # Primero verificar si hay leads
    from db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        print("⚠️ La tabla leads está vacía")
        create_sample = input("¿Quieres crear algunos leads de prueba? (y/n): ")
        if create_sample.lower() == 'y':
            create_sample_leads()
    
    # Aplicar correcciones
    if fix_leads_table():
        test_api_after_fix()
        
        print(f"\n💡 PRÓXIMOS PASOS:")
        print("1. Reinicia tu servidor Flask")
        print("2. Recarga la página calls-manager")
        print("3. Deberías ver los leads en la tabla")

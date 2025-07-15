#!/usr/bin/env python3
"""
Script para marcar leads como seleccionados para pruebas de llamadas
"""

def mark_leads_for_testing():
    print("🧪 === MARCANDO LEADS PARA PRUEBAS ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Marcar los leads como seleccionados para llamar
        cursor.execute("""
            UPDATE leads 
            SET selected_for_calling = TRUE, 
                call_status = 'selected'
            WHERE (telefono IS NOT NULL AND telefono != '') 
               OR (telefono2 IS NOT NULL AND telefono2 != '')
        """)
        
        updated = cursor.rowcount
        conn.commit()
        
        print(f"✅ Marcados {updated} leads como seleccionados para llamar")
        
        # Mostrar estado actual
        cursor.execute("""
            SELECT id, nombre, telefono, call_status, selected_for_calling 
            FROM leads 
            WHERE selected_for_calling = TRUE
        """)
        
        leads = cursor.fetchall()
        print(f"\n📋 Leads seleccionados:")
        for lead in leads:
            print(f"  ID: {lead[0]}, Nombre: {lead[1]}, Tel: {lead[2]}, Estado: {lead[3]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if mark_leads_for_testing():
        print(f"\n💡 PRÓXIMOS PASOS:")
        print("1. Reinicia tu servidor Flask")
        print("2. Recarga la página calls-manager")
        print("3. Los leads deberían aparecer como seleccionados (con checkboxes marcados)")
        print("4. Ahora puedes hacer clic en 'INICIAR' para probar las llamadas")

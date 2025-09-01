#!/usr/bin/env python3
from db import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM leads")
    total = cursor.fetchone()[0]
    print(f"Total leads: {total}")
    
    if total > 0:
        cursor.execute("""
            SELECT COUNT(*) FROM leads 
            WHERE ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (manual_management IS NULL OR manual_management = FALSE)
        """)
        elegibles = cursor.fetchone()[0]
        print(f"Leads elegibles para API: {elegibles}")
        
        if elegibles > 0:
            cursor.execute("""
                SELECT id, nombre, apellidos, telefono, selected_for_calling 
                FROM leads 
                WHERE ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
                AND (manual_management IS NULL OR manual_management = FALSE)
                LIMIT 3
            """)
            ejemplos = cursor.fetchall()
            print("\nEjemplos:")
            for lead in ejemplos:
                print(f"  ID {lead[0]}: {lead[1]} {lead[2]} - Tel: {lead[3]} - Selected: {lead[4]}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
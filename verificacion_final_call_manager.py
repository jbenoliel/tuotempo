#!/usr/bin/env python3
"""
Verificacion final completa para entender exactamente que ve el call-manager
"""

import pymysql

# Configuracion de Railway
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    return pymysql.connect(**RAILWAY_CONFIG)

def verificacion_final():
    """Verificacion final completa del estado de leads"""

    print("=== VERIFICACION FINAL CALL-MANAGER ===")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Parametros de busqueda
        estado1 = 'Volver a llamar'
        origen_archivo = 'SEGURCAIXA_JULIO'

        print("CONTEOS DETALLADOS:")
        print("=" * 50)

        # 1. Total con estado y origen
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
        """, [estado1, origen_archivo])
        total_estado_origen = cursor.fetchone()[0]
        print(f"1. Total con estado '{estado1}' y origen '{origen_archivo}': {total_estado_origen}")

        # 2. Con telefono valido
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
        """, [estado1, origen_archivo])
        con_telefono = cursor.fetchone()[0]
        print(f"2. + con telefono valido: {con_telefono}")

        # 3. + lead_status open
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (lead_status IS NULL OR lead_status = 'open')
        """, [estado1, origen_archivo])
        lead_status_open = cursor.fetchone()[0]
        print(f"3. + lead_status open: {lead_status_open}")

        # 4. + sin cita programada
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (lead_status IS NULL OR lead_status = 'open')
            AND (status_level_2 IS NULL OR status_level_2 != 'Cita programada')
        """, [estado1, origen_archivo])
        sin_cita = cursor.fetchone()[0]
        print(f"4. + sin 'Cita programada': {sin_cita}")

        # 5. + no seleccionados
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (lead_status IS NULL OR lead_status = 'open')
            AND (status_level_2 IS NULL OR status_level_2 != 'Cita programada')
            AND selected_for_calling = FALSE
        """, [estado1, origen_archivo])
        no_seleccionados = cursor.fetchone()[0]
        print(f"5. + no seleccionados (selected_for_calling = FALSE): {no_seleccionados}")

        # 6. + manual_management
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (lead_status IS NULL OR lead_status = 'open')
            AND (status_level_2 IS NULL OR status_level_2 != 'Cita programada')
            AND selected_for_calling = FALSE
            AND (manual_management IS NULL OR manual_management = FALSE)
        """, [estado1, origen_archivo])
        final_disponibles = cursor.fetchone()[0]
        print(f"6. + manual_management OK: {final_disponibles}")

        print()

        # Estado de selected_for_calling
        print("ESTADO DE SELECTED_FOR_CALLING:")
        print("=" * 50)

        cursor.execute("""
            SELECT selected_for_calling, COUNT(*) as count
            FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (lead_status IS NULL OR lead_status = 'open')
            AND (status_level_2 IS NULL OR status_level_2 != 'Cita programada')
            GROUP BY selected_for_calling
        """, [estado1, origen_archivo])

        selected_distribution = cursor.fetchall()
        for selected, count in selected_distribution:
            selected_str = 'TRUE' if selected else 'FALSE' if selected is False else 'NULL'
            print(f"   selected_for_calling = {selected_str}: {count} leads")

        print()

        # Verificar call_status de los seleccionados
        print("CALL_STATUS DE LEADS SELECCIONADOS:")
        print("=" * 50)

        cursor.execute("""
            SELECT call_status, COUNT(*) as count
            FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND selected_for_calling = TRUE
            GROUP BY call_status
        """, [estado1, origen_archivo])

        call_status_selected = cursor.fetchall()
        if call_status_selected:
            for call_status, count in call_status_selected:
                status_str = call_status if call_status else 'NULL'
                print(f"   call_status = {status_str}: {count} leads seleccionados")
        else:
            print("   No hay leads seleccionados actualmente")

        print()

        # Ejemplos de leads disponibles
        print("EJEMPLOS DE LEADS DISPONIBLES:")
        print("=" * 50)

        cursor.execute("""
            SELECT id, nombre, telefono, status_level_2, lead_status,
                   selected_for_calling, call_status, updated_at
            FROM leads
            WHERE status_level_1 = %s AND origen_archivo = %s
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (lead_status IS NULL OR lead_status = 'open')
            AND (status_level_2 IS NULL OR status_level_2 != 'Cita programada')
            AND selected_for_calling = FALSE
            AND (manual_management IS NULL OR manual_management = FALSE)
            LIMIT 3
        """, [estado1, origen_archivo])

        ejemplos = cursor.fetchall()
        if ejemplos:
            for id, nombre, telefono, status2, lead_status, selected, call_status, updated in ejemplos:
                print(f"   Lead {id}: {nombre}")
                print(f"      telefono: {telefono}")
                print(f"      status_level_2: {status2}")
                print(f"      lead_status: {lead_status}")
                print(f"      selected_for_calling: {selected}")
                print(f"      call_status: {call_status}")
                print(f"      updated_at: {updated}")
                print()
        else:
            print("   ¡NO SE ENCONTRARON LEADS DISPONIBLES!")

        print("CONCLUSION:")
        print("=" * 50)
        print(f"Leads disponibles para call-manager: {final_disponibles}")

        if final_disponibles > 0:
            print("[OK] HAY LEADS DISPONIBLES")
            print("Si el call-manager no los muestra:")
            print("- Verifica cache del navegador (Ctrl+F5)")
            print("- Verifica la URL del call-manager")
            print("- Verifica la consola del navegador (F12)")
        else:
            print("[PROBLEMA] NO HAY LEADS DISPONIBLES")
            print("Todos los leads estan seleccionados o tienen algun filtro activo")

        return final_disponibles

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    disponibles = verificacion_final()
    print()
    print("=" * 60)
    if disponibles > 0:
        print("[EXITO] Hay leads disponibles en la base de datos")
    else:
        print("[PROBLEMA] No hay leads disponibles")
    print("Verifica ahora el call-manager")
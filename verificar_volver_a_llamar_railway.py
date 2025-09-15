#!/usr/bin/env python3
"""
Verifica el problema de leads con 'Volver a llamar' que no aparecen en call-manager
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

def investigar_volver_a_llamar():
    """Investiga el problema con leads 'Volver a llamar'"""

    print("=== INVESTIGACION: LEADS 'VOLVER A LLAMAR' ===")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Verificar nuevos leads problematicos
        leads_problematicos = [2407, 2399, 2133, 2422, 2000]
        print("1. VERIFICANDO NUEVOS LEADS PROBLEMATICOS:")

        for lead_id in leads_problematicos:
            cursor.execute("""
                SELECT id, lead_status, status_level_1, archivo_origen,
                       call_attempts_count, call_status, telefono, nombre
                FROM leads
                WHERE id = %s
            """, (lead_id,))

            lead = cursor.fetchone()
            if lead:
                id, lead_status, status_level_1, archivo_origen, attempts, call_status, telefono, nombre = lead
                print(f"   Lead {id}: {lead_status}, {status_level_1}, archivo={archivo_origen}, intentos={attempts}")
            else:
                print(f"   Lead {lead_id}: NO EXISTE")

        print()

        # 2. Contar leads con 'Volver a llamar' total
        print("2. CONTEO TOTAL DE LEADS 'VOLVER A LLAMAR':")
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE status_level_1 = 'Volver a llamar'
        """)
        total_volver_llamar = cursor.fetchone()[0]
        print(f"   Total con 'Volver a llamar': {total_volver_llamar}")

        # 3. Contar por estado del lead
        cursor.execute("""
            SELECT lead_status, COUNT(*) as count
            FROM leads
            WHERE status_level_1 = 'Volver a llamar'
            GROUP BY lead_status
        """)
        estados = cursor.fetchall()
        print("   Distribucion por estado:")
        for estado, count in estados:
            print(f"     {estado}: {count}")

        print()

        # 4. Verificar consulta tipica del call-manager
        print("3. SIMULANDO CONSULTA DEL CALL-MANAGER:")

        # Esta seria la consulta tipica que usa call-manager
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads l
            WHERE l.lead_status = 'open'
            AND l.status_level_1 = 'Volver a llamar'
            AND l.archivo_origen IN ('SEGURCAIXA_JULIO')
            AND l.selected_for_calling = FALSE
            AND (l.call_status IS NULL OR l.call_status != 'in_progress')
        """)
        disponibles_call_manager = cursor.fetchone()[0]
        print(f"   Leads disponibles para call-manager: {disponibles_call_manager}")

        # 5. Verificar que no estan seleccionados
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads l
            WHERE l.lead_status = 'open'
            AND l.status_level_1 = 'Volver a llamar'
            AND l.archivo_origen IN ('SEGURCAIXA_JULIO')
            AND l.selected_for_calling = TRUE
        """)
        ya_seleccionados = cursor.fetchone()[0]
        print(f"   Leads ya seleccionados: {ya_seleccionados}")

        # 6. Verificar en progreso
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads l
            WHERE l.lead_status = 'open'
            AND l.status_level_1 = 'Volver a llamar'
            AND l.archivo_origen IN ('SEGURCAIXA_JULIO')
            AND l.call_status = 'in_progress'
        """)
        en_progreso = cursor.fetchone()[0]
        print(f"   Leads en progreso: {en_progreso}")

        print()

        # 7. Mostrar algunos ejemplos
        print("4. EJEMPLOS DE LEADS 'VOLVER A LLAMAR' ABIERTOS:")
        cursor.execute("""
            SELECT id, nombre, telefono, call_attempts_count,
                   selected_for_calling, call_status
            FROM leads l
            WHERE l.lead_status = 'open'
            AND l.status_level_1 = 'Volver a llamar'
            AND l.archivo_origen IN ('SEGURCAIXA_JULIO')
            LIMIT 5
        """)
        ejemplos = cursor.fetchall()

        for id, nombre, telefono, attempts, selected, call_status in ejemplos:
            selected_str = 'SI' if selected else 'NO'
            status_str = call_status or 'NULL'
            print(f"   Lead {id}: {nombre}, tel={telefono}, intentos={attempts}, seleccionado={selected_str}, status={status_str}")

        print()

        # 8. Verificar archivo_origen formato
        print("5. VERIFICANDO FORMATO DE ARCHIVO_ORIGEN:")
        cursor.execute("""
            SELECT DISTINCT archivo_origen, COUNT(*) as count
            FROM leads
            WHERE status_level_1 = 'Volver a llamar'
            AND lead_status = 'open'
            GROUP BY archivo_origen
            ORDER BY count DESC
            LIMIT 10
        """)
        archivos = cursor.fetchall()

        for archivo, count in archivos:
            print(f"   '{archivo}': {count} leads")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    investigar_volver_a_llamar()
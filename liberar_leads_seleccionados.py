#!/usr/bin/env python3
"""
Libera leads que estan marcados como selected_for_calling = TRUE
para que puedan ser seleccionados nuevamente en call-manager
"""

import pymysql
from datetime import datetime

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

def liberar_leads_seleccionados():
    """Libera leads seleccionados para que puedan ser usados nuevamente"""

    print("=== LIBERACION DE LEADS SELECCIONADOS ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Estado inicial
        print("1. ESTADO INICIAL:")

        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE selected_for_calling = TRUE
        """)
        total_seleccionados = cursor.fetchone()[0]
        print(f"   Total leads seleccionados: {total_seleccionados}")

        # Especificamente SEGURCAIXA_JULIO con 'Volver a llamar'
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Volver a llamar'
            AND selected_for_calling = TRUE
        """)
        segurcaixa_seleccionados = cursor.fetchone()[0]
        print(f"   SEGURCAIXA_JULIO 'Volver a llamar' seleccionados: {segurcaixa_seleccionados}")

        print()

        # 2. Verificar cuales estan realmente en progreso
        print("2. VERIFICANDO LEADS EN PROGRESO REAL:")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE selected_for_calling = TRUE
            AND call_status = 'in_progress'
        """)
        realmente_en_progreso = cursor.fetchone()[0]
        print(f"   Realmente en progreso (call_status = 'in_progress'): {realmente_en_progreso}")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE selected_for_calling = TRUE
            AND call_status != 'in_progress'
        """)
        bloqueados_sin_razon = cursor.fetchone()[0]
        print(f"   Bloqueados sin estar en progreso: {bloqueados_sin_razon}")

        print()

        # 3. Liberar leads que no estan realmente en progreso
        print("3. LIBERANDO LEADS BLOQUEADOS:")

        cursor.execute("""
            UPDATE leads
            SET selected_for_calling = FALSE,
                updated_at = NOW()
            WHERE selected_for_calling = TRUE
            AND (call_status IS NULL OR call_status != 'in_progress')
        """)
        liberados = cursor.rowcount
        print(f"   Leads liberados: {liberados}")

        # 4. Verificar estado final especifico de SEGURCAIXA_JULIO
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Volver a llamar'
            AND (lead_status IS NULL OR lead_status = 'open')
            AND (status_level_2 IS NULL OR status_level_2 != 'Cita programada')
            AND selected_for_calling = FALSE
        """)
        disponibles_ahora = cursor.fetchone()[0]
        print(f"   SEGURCAIXA_JULIO 'Volver a llamar' disponibles ahora: {disponibles_ahora}")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Volver a llamar'
            AND selected_for_calling = TRUE
        """)
        aun_seleccionados = cursor.fetchone()[0]
        print(f"   SEGURCAIXA_JULIO 'Volver a llamar' aun seleccionados: {aun_seleccionados}")

        conn.commit()

        print()
        print("4. RESULTADO FINAL:")
        print(f"   Leads liberados total: {liberados}")
        print(f"   SEGURCAIXA_JULIO disponibles para call-manager: {disponibles_ahora}")

        if disponibles_ahora > 0:
            print(f"   [EXITO] Ahora el call-manager deberia mostrar {disponibles_ahora} leads disponibles")
        else:
            print(f"   [ATENCION] Aun no hay leads disponibles, verificar otros criterios")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if liberar_leads_seleccionados():
        print()
        print("=" * 60)
        print("[COMPLETADO] LIBERACION DE LEADS EXITOSA")
        print("El call-manager deberia mostrar leads disponibles ahora")
    else:
        print()
        print("[ERROR] La liberacion fallo")
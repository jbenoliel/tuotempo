#!/usr/bin/env python3
"""
Fuerza un refresh de los leads 'Volver a llamar' actualizando timestamps
para asegurar que el call-manager los detecte correctamente
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

def forzar_refresh_leads():
    """Fuerza refresh de leads para que call-manager los detecte"""

    print("=== FORZANDO REFRESH DE LEADS 'VOLVER A LLAMAR' ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Estado actual exacto
        print("1. VERIFICACION ESTADO ACTUAL:")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
            AND selected_for_calling = FALSE
        """)
        disponibles = cursor.fetchone()[0]
        print(f"   Leads disponibles para call-manager: {disponibles}")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND selected_for_calling = TRUE
        """)
        seleccionados = cursor.fetchone()[0]
        print(f"   Leads ya seleccionados: {seleccionados}")

        print()

        # 2. Forzar actualizacion de timestamps para "despertar" el sistema
        print("2. FORZANDO ACTUALIZACION DE TIMESTAMPS:")

        cursor.execute("""
            UPDATE leads
            SET updated_at = NOW()
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
        """)
        actualizados = cursor.rowcount
        print(f"   Timestamps actualizados: {actualizados} leads")

        # 3. Asegurar que selected_for_calling este en FALSE
        print("3. ASEGURANDO ESTADO CORRECTO DE SELECCION:")

        cursor.execute("""
            UPDATE leads
            SET selected_for_calling = FALSE,
                updated_at = NOW()
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
            AND selected_for_calling = TRUE
        """)
        liberados = cursor.rowcount
        print(f"   Leads liberados adicionalmente: {liberados}")

        # 4. Verificar ejemplos especificos
        print("4. MUESTRA DE LEADS DISPONIBLES:")
        cursor.execute("""
            SELECT id, nombre, telefono, status_level_1, status_level_2,
                   lead_status, selected_for_calling, updated_at
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
            AND selected_for_calling = FALSE
            LIMIT 3
        """)
        ejemplos = cursor.fetchall()

        for id, nombre, telefono, status1, status2, lead_status, selected, updated in ejemplos:
            selected_str = 'SI' if selected else 'NO'
            print(f"   Lead {id}: {nombre}, tel={telefono}")
            print(f"       status1='{status1}', status2='{status2}'")
            print(f"       lead_status='{lead_status}', seleccionado={selected_str}")
            print(f"       updated_at={updated}")
            print()

        conn.commit()

        print("5. INSTRUCCIONES PARA TESTING:")
        print("   a) Ve al call-manager")
        print("   b) Selecciona status_level_1 = 'Volver a llamar'")
        print("   c) Selecciona archivo_origen = 'SEGURCAIXA_JULIO'")
        print(f"   d) Deberia mostrar {disponibles + liberados} leads disponibles")
        print()

        print("6. SI AUN NO FUNCIONA:")
        print("   - El problema podria ser cache del navegador/frontend")
        print("   - Intenta refrescar la pagina (Ctrl+F5)")
        print("   - Verifica la consola del navegador para errores JavaScript")
        print("   - Verifica logs del servidor para errores de API")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if forzar_refresh_leads():
        print()
        print("=" * 60)
        print("[COMPLETADO] REFRESH FORZADO EXITOSAMENTE")
        print("Intenta usar el call-manager ahora")
    else:
        print()
        print("[ERROR] El refresh fallo")
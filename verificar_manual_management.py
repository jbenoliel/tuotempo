#!/usr/bin/env python3
"""
Verifica si los leads SEGURCAIXA_JULIO tienen manual_management = TRUE
que los excluiria de la seleccion del call-manager
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

def verificar_manual_management():
    """Verifica el campo manual_management en leads SEGURCAIXA_JULIO"""

    print("=== VERIFICACION MANUAL_MANAGEMENT ===")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Verificar distribucion de manual_management
        print("1. DISTRIBUCION DE MANUAL_MANAGEMENT:")

        cursor.execute("""
            SELECT manual_management, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            GROUP BY manual_management
        """)
        distribucion = cursor.fetchall()

        total_leads = 0
        for manual_mgmt, count in distribucion:
            manual_str = 'TRUE' if manual_mgmt else ('FALSE' if manual_mgmt is False else 'NULL')
            print(f"   manual_management = {manual_str}: {count} leads")
            total_leads += count

        print(f"   Total: {total_leads} leads")
        print()

        # 2. Consulta SIN filtro de manual_management (actual)
        print("2. CONSULTA ACTUAL (SIN FILTRO MANUAL_MANAGEMENT):")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
            AND selected_for_calling = FALSE
        """)
        sin_filtro = cursor.fetchone()[0]
        print(f"   Disponibles sin filtro manual_management: {sin_filtro}")

        # 3. Consulta CON filtro de manual_management
        print("3. CONSULTA CON FILTRO MANUAL_MANAGEMENT:")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
            AND selected_for_calling = FALSE
            AND (manual_management IS NULL OR manual_management = FALSE)
        """)
        con_filtro = cursor.fetchone()[0]
        print(f"   Disponibles con filtro manual_management: {con_filtro}")

        diferencia = sin_filtro - con_filtro
        print(f"   Diferencia (excluidos): {diferencia}")
        print()

        # 4. Mostrar ejemplos de leads con manual_management = TRUE
        print("4. EJEMPLOS DE LEADS CON MANUAL_MANAGEMENT = TRUE:")
        cursor.execute("""
            SELECT id, nombre, telefono, manual_management
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND manual_management = TRUE
            LIMIT 5
        """)
        ejemplos_manual = cursor.fetchall()

        if ejemplos_manual:
            for id, nombre, telefono, manual_mgmt in ejemplos_manual:
                print(f"   Lead {id}: {nombre}, tel={telefono}, manual_management={manual_mgmt}")
        else:
            print("   No se encontraron leads con manual_management = TRUE")

        print()

        # 5. Verificar si esta es la causa del problema
        print("5. DIAGNOSTICO:")
        if diferencia > 0:
            print(f"   [PROBLEMA ENCONTRADO] {diferencia} leads excluidos por manual_management = TRUE")
            print("   Esto explica por que el call-manager no los encuentra")
            print()
            print("   SOLUCION:")
            print("   - Cambiar manual_management = FALSE en estos leads")
            print("   - O verificar si realmente deben estar en gestion manual")
        elif con_filtro == 0:
            print("   [PROBLEMA DIFERENTE] El filtro manual_management no es la causa")
            print("   Buscar otros filtros o condiciones")
        else:
            print(f"   [OK] {con_filtro} leads disponibles con todos los filtros")

        return diferencia, con_filtro

    except Exception as e:
        print(f"ERROR: {e}")
        return 0, 0
    finally:
        cursor.close()
        conn.close()

def corregir_manual_management():
    """Corrige manual_management en leads que no deberian estar en gestion manual"""

    print()
    print("=== CORRECCION MANUAL_MANAGEMENT ===")
    print()

    respuesta = input("¿Quieres cambiar manual_management = FALSE en leads SEGURCAIXA_JULIO 'Volver a llamar'? (s/n): ").strip().lower()

    if respuesta != 's':
        print("Correccion cancelada")
        return False

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE leads
            SET manual_management = FALSE,
                updated_at = NOW()
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND manual_management = TRUE
        """)
        corregidos = cursor.rowcount

        conn.commit()

        print(f"   Leads corregidos: {corregidos}")
        print("   Estos leads ahora deberian aparecer en call-manager")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    diferencia, disponibles = verificar_manual_management()

    if diferencia > 0:
        corregir_manual_management()
        print()
        print("=" * 60)
        print("VERIFICA AHORA EL CALL-MANAGER")
        print("Deberia mostrar los leads disponibles")
    else:
        print()
        print("=" * 60)
        print("MANUAL_MANAGEMENT NO ES LA CAUSA DEL PROBLEMA")
        print("Hay que seguir investigando otros filtros")
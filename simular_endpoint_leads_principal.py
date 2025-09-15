#!/usr/bin/env python3
"""
Simula exactamente el endpoint /leads que usa el call-manager
para encontrar el filtro que excluye los leads 'Volver a llamar'
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

def simular_endpoint_leads():
    """Simula exactamente el endpoint /leads del call-manager"""

    print("=== SIMULACION ENDPOINT /leads ===")
    print()

    # Parametros que enviaria el call-manager
    estado1 = 'Volver a llamar'
    origen_archivos = ['SEGURCAIXA_JULIO']
    selected_only = False  # Para ver todos, no solo seleccionados
    limit = 25
    offset = 0

    print(f"Parametros:")
    print(f"  estado1: '{estado1}'")
    print(f"  origen_archivo: {origen_archivos}")
    print(f"  selected_only: {selected_only}")
    print(f"  limit: {limit}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Construir query igual que el endpoint
        conditions = []
        params = []

        # Filtro base: al menos un telefono valido
        conditions.append("((l.telefono IS NOT NULL AND l.telefono != '') OR (l.telefono2 IS NOT NULL AND l.telefono2 != ''))")

        # Filtro: excluir leads gestionados manualmente
        conditions.append("(l.manual_management IS NULL OR l.manual_management = FALSE)")

        # Filtro por estado1
        if estado1:
            conditions.append("l.status_level_1 = %s")
            params.append(estado1)

        # Filtro por selected_only
        if selected_only:
            conditions.append("l.selected_for_calling = TRUE")

        # Filtro por archivo de origen
        if origen_archivos:
            origen_archivos_filtrados = [archivo for archivo in origen_archivos if archivo.strip()]
            if origen_archivos_filtrados:
                placeholders = ', '.join(['%s'] * len(origen_archivos_filtrados))
                conditions.append(f"l.origen_archivo IN ({placeholders})")
                params.extend(origen_archivos_filtrados)

        # Query principal (simplificada para contar)
        where_clause = " AND ".join(conditions)

        print("1. CONSULTA COMPLETA DEL ENDPOINT /leads:")
        query = f"SELECT COUNT(*) as count FROM leads l WHERE {where_clause}"
        print(f"   Query: {query}")
        print(f"   Params: {params}")

        cursor.execute(query, params)
        count_endpoint_leads = cursor.fetchone()[0]
        print(f"   Resultado: {count_endpoint_leads} leads")
        print()

        # Verificar paso a paso cada filtro
        print("2. VERIFICACION PASO A PASO:")

        # Solo telefono valido
        cursor.execute("SELECT COUNT(*) FROM leads l WHERE ((l.telefono IS NOT NULL AND l.telefono != '') OR (l.telefono2 IS NOT NULL AND l.telefono2 != ''))")
        paso1 = cursor.fetchone()[0]
        print(f"   Paso 1 - Con telefono valido: {paso1}")

        # + manual_management
        cursor.execute("SELECT COUNT(*) FROM leads l WHERE ((l.telefono IS NOT NULL AND l.telefono != '') OR (l.telefono2 IS NOT NULL AND l.telefono2 != '')) AND (l.manual_management IS NULL OR l.manual_management = FALSE)")
        paso2 = cursor.fetchone()[0]
        print(f"   Paso 2 - + manual_management: {paso2}")

        # + status_level_1
        cursor.execute("SELECT COUNT(*) FROM leads l WHERE ((l.telefono IS NOT NULL AND l.telefono != '') OR (l.telefono2 IS NOT NULL AND l.telefono2 != '')) AND (l.manual_management IS NULL OR l.manual_management = FALSE) AND l.status_level_1 = %s", [estado1])
        paso3 = cursor.fetchone()[0]
        print(f"   Paso 3 - + status_level_1: {paso3}")

        # + origen_archivo
        cursor.execute(f"SELECT COUNT(*) FROM leads l WHERE ((l.telefono IS NOT NULL AND l.telefono != '') OR (l.telefono2 IS NOT NULL AND l.telefono2 != '')) AND (l.manual_management IS NULL OR l.manual_management = FALSE) AND l.status_level_1 = %s AND l.origen_archivo IN ({placeholders})", [estado1] + origen_archivos_filtrados)
        paso4 = cursor.fetchone()[0]
        print(f"   Paso 4 - + origen_archivo: {paso4}")

        print()

        # Verificar leads sin telefono
        print("3. VERIFICACION DE TELEFONOS:")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (telefono IS NULL OR telefono = '')
            AND (telefono2 IS NULL OR telefono2 = '')
        """)
        sin_telefono = cursor.fetchone()[0]
        print(f"   Leads sin telefono valido: {sin_telefono}")

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
        """)
        con_telefono = cursor.fetchone()[0]
        print(f"   Leads con telefono valido: {con_telefono}")

        # Mostrar ejemplos sin telefono si los hay
        if sin_telefono > 0:
            print()
            print("   Ejemplos sin telefono valido:")
            cursor.execute("""
                SELECT id, nombre, telefono, telefono2
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND TRIM(status_level_1) = 'Volver a llamar'
                AND (telefono IS NULL OR telefono = '')
                AND (telefono2 IS NULL OR telefono2 = '')
                LIMIT 3
            """)
            ejemplos = cursor.fetchall()
            for id, nombre, tel1, tel2 in ejemplos:
                tel1_str = repr(tel1) if tel1 else 'NULL'
                tel2_str = repr(tel2) if tel2 else 'NULL'
                print(f"     Lead {id}: {nombre}, tel1={tel1_str}, tel2={tel2_str}")

        print()

        # Diagnostico final
        print("4. DIAGNOSTICO:")
        if count_endpoint_leads == 0:
            print("   [PROBLEMA ENCONTRADO] El endpoint /leads devuelve 0 resultados")
            if sin_telefono > 0:
                print(f"   CAUSA: {sin_telefono} leads no tienen telefono valido")
                print("   SOLUCION: Verificar/corregir telefonos en SEGURCAIXA_JULIO")
            else:
                print("   CAUSA: Otro filtro desconocido")
        else:
            print(f"   [OK] El endpoint /leads devuelve {count_endpoint_leads} leads")
            print("   El problema debe estar en otro lado")

        return count_endpoint_leads

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    simular_endpoint_leads()
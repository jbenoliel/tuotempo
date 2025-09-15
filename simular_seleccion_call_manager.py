#!/usr/bin/env python3
"""
Simula exactamente la operacion que hace el call-manager
para seleccionar leads con 'Volver a llamar'
"""

import pymysql
import json

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

def simular_seleccion_call_manager():
    """Simula exactamente la seleccion del call-manager"""

    print("=== SIMULACION SELECCION CALL-MANAGER ===")
    print()

    # Parametros exactos como el call-manager los envia
    status_field = 'status_level_1'
    status_value = 'Volver a llamar'
    archivo_origen = ['SEGURCAIXA_JULIO']
    selected = True

    print(f"Parametros de seleccion:")
    print(f"  status_field: '{status_field}'")
    print(f"  status_value: '{status_value}'")
    print(f"  archivo_origen: {archivo_origen}")
    print(f"  selected: {selected}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # PASO 1: Consulta de conteo (como count-by-status)
        print("1. SIMULACION CONSULTA DE CONTEO:")

        where_conditions = [f"TRIM({status_field}) = %s"]
        params = [status_value]

        where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")
        where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")

        if archivo_origen:
            placeholders = ','.join(['%s'] * len(archivo_origen))
            where_conditions.append(f"origen_archivo IN ({placeholders})")
            params.extend(archivo_origen)

        where_clause = ' AND '.join(where_conditions)

        # Contar total
        query_total = f"SELECT COUNT(*) as total FROM leads WHERE {where_clause}"
        cursor.execute(query_total, params)
        total_count = cursor.fetchone()[0]
        print(f"   Total que cumple criterios: {total_count}")

        # Contar ya seleccionados
        where_conditions.append("selected_for_calling = 1")
        where_clause_selected = ' AND '.join(where_conditions)
        query_selected = f"SELECT COUNT(*) as selected FROM leads WHERE {where_clause_selected}"
        cursor.execute(query_selected, params)
        selected_count = cursor.fetchone()[0]

        available_count = total_count - selected_count
        print(f"   Ya seleccionados: {selected_count}")
        print(f"   Disponibles para seleccionar: {available_count}")
        print()

        # PASO 2: Simulacion de seleccion (como select-by-status)
        print("2. SIMULACION OPERACION DE SELECCION:")

        # Resetear where_conditions para la actualizacion
        where_conditions = [f"TRIM({status_field}) = %s"]
        params = [status_value]
        where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")
        where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")

        if archivo_origen:
            placeholders = ','.join(['%s'] * len(archivo_origen))
            where_conditions.append(f"origen_archivo IN ({placeholders})")
            params.extend(archivo_origen)

        where_clause = ' AND '.join(where_conditions)

        # Esta es la consulta exacta del endpoint select-by-status
        update_query = f"""
            UPDATE leads
            SET selected_for_calling = %s,
                updated_at = NOW()
            WHERE {where_clause}
        """

        print(f"   Query de actualizacion: {update_query}")
        print(f"   Parametros: {[1 if selected else 0] + params}")

        # Ejecutar SIN commit para ver cuantos afectaria
        cursor.execute(update_query, [1 if selected else 0] + params)
        affected_count = cursor.rowcount

        print(f"   Leads que serian afectados: {affected_count}")

        # NO hacer commit para no cambiar nada, solo simular
        conn.rollback()

        print()

        # PASO 3: Verificar si hay algun problema con los datos
        print("3. ANALISIS DETALLADO DE PROBLEMAS POTENCIALES:")

        # Verificar leads con espacios o caracteres raros
        cursor.execute(f"""
            SELECT id, nombre, CHAR_LENGTH(TRIM(status_level_1)) as len,
                   HEX(status_level_1) as hex_value,
                   status_level_1
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 LIKE '%Volver a llamar%'
            LIMIT 5
        """)

        problematicos = cursor.fetchall()
        if problematicos:
            print("   Muestra de status_level_1 con potenciales problemas:")
            for id, nombre, length, hex_val, status in problematicos:
                print(f"     Lead {id}: len={length}, hex={hex_val}, valor='{status}'")

        # Verificar leads con status_level_2 problematico
        cursor.execute(f"""
            SELECT status_level_2, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            GROUP BY status_level_2
            ORDER BY count DESC
        """)

        status2_dist = cursor.fetchall()
        print("   Distribucion de status_level_2:")
        for status2, count in status2_dist:
            status2_repr = repr(status2) if status2 else 'NULL'
            excluded = "(EXCLUIDO)" if status2 == 'Cita programada' else ""
            print(f"     {status2_repr}: {count} {excluded}")

        # Verificar leads con lead_status problematico
        cursor.execute(f"""
            SELECT lead_status, COUNT(*) as count
            FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND TRIM(status_level_1) = 'Volver a llamar'
            GROUP BY lead_status
        """)

        lead_status_dist = cursor.fetchall()
        print("   Distribucion de lead_status:")
        for lead_status, count in lead_status_dist:
            status_repr = repr(lead_status) if lead_status else 'NULL'
            excluded = "" if not lead_status or lead_status == 'open' else "(EXCLUIDO)"
            print(f"     {status_repr}: {count} {excluded}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    simular_seleccion_call_manager()
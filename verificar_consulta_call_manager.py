#!/usr/bin/env python3
"""
Verifica exactamente la misma consulta que usa el call-manager
para diagnosticar por que no encuentra leads 'Volver a llamar'
"""

import pymysql
from urllib.parse import unquote_plus

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

def verificar_consulta_call_manager():
    """Replica exactamente la consulta del call-manager"""

    print("=== VERIFICACION CONSULTA CALL-MANAGER ===")
    print()

    # Parametros de la consulta real
    status_field = 'status_level_1'
    status_value = unquote_plus('Volver+a+llamar')  # Decodificar URL
    archivo_origen = ['SEGURCAIXA_JULIO']

    print(f"Parametros de busqueda:")
    print(f"  status_field: {status_field}")
    print(f"  status_value: '{status_value}'")
    print(f"  archivo_origen: {archivo_origen}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # PASO 1: Replica exacta de la consulta del call-manager
        print("1. CONSULTA EXACTA DEL CALL-MANAGER:")

        where_conditions = [f"TRIM({status_field}) = %s"]
        params = [status_value]

        # CRITICO: Solo leads OPEN
        where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")

        # CRITICO: Excluir leads con cita programada
        where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")

        # Filtro de archivo origen
        if archivo_origen:
            placeholders = ','.join(['%s'] * len(archivo_origen))
            where_conditions.append(f"origen_archivo IN ({placeholders})")
            params.extend(archivo_origen)

        where_clause = ' AND '.join(where_conditions)
        query_total = f"SELECT COUNT(*) as total FROM leads WHERE {where_clause}"

        print(f"   Query: {query_total}")
        print(f"   Params: {params}")

        cursor.execute(query_total, params)
        total_count = cursor.fetchone()[0]
        print(f"   Resultado: {total_count} leads")
        print()

        # PASO 2: Verificar cada condicion por separado
        print("2. VERIFICACION POR CONDICIONES:")

        # Solo status_level_1
        cursor.execute(f"SELECT COUNT(*) FROM leads WHERE TRIM({status_field}) = %s", [status_value])
        solo_status = cursor.fetchone()[0]
        print(f"   Solo status_level_1 = '{status_value}': {solo_status}")

        # Status + open
        cursor.execute(f"SELECT COUNT(*) FROM leads WHERE TRIM({status_field}) = %s AND (lead_status IS NULL OR TRIM(lead_status) = 'open')", [status_value])
        status_open = cursor.fetchone()[0]
        print(f"   + solo leads open: {status_open}")

        # Status + open + sin cita programada
        cursor.execute(f"SELECT COUNT(*) FROM leads WHERE TRIM({status_field}) = %s AND (lead_status IS NULL OR TRIM(lead_status) = 'open') AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')", [status_value])
        sin_cita = cursor.fetchone()[0]
        print(f"   + sin 'Cita programada': {sin_cita}")

        # Status + open + sin cita + archivo origen
        if archivo_origen:
            cursor.execute(f"SELECT COUNT(*) FROM leads WHERE TRIM({status_field}) = %s AND (lead_status IS NULL OR TRIM(lead_status) = 'open') AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada') AND origen_archivo IN ({placeholders})", [status_value] + archivo_origen)
            con_archivo = cursor.fetchone()[0]
            print(f"   + archivo SEGURCAIXA_JULIO: {con_archivo}")

        print()

        # PASO 3: Verificar leads seleccionados
        print("3. LEADS YA SELECCIONADOS:")
        where_conditions.append("selected_for_calling = 1")
        where_clause_selected = ' AND '.join(where_conditions)
        query_selected = f"SELECT COUNT(*) as selected FROM leads WHERE {where_clause_selected}"
        cursor.execute(query_selected, params)
        selected_count = cursor.fetchone()[0]
        print(f"   Ya seleccionados para llamar: {selected_count}")
        print(f"   Disponibles para seleccionar: {total_count - selected_count}")
        print()

        # PASO 4: Mostrar ejemplos de leads que cumplen criterios
        print("4. EJEMPLOS DE LEADS QUE CUMPLEN CRITERIOS:")
        query_ejemplos = f"SELECT id, nombre, telefono, status_level_1, status_level_2, lead_status, origen_archivo, selected_for_calling FROM leads WHERE {where_clause} LIMIT 5"
        cursor.execute(query_ejemplos, params)
        ejemplos = cursor.fetchall()

        if ejemplos:
            for id, nombre, telefono, status1, status2, lead_status, origen, selected in ejemplos:
                selected_str = 'SI' if selected else 'NO'
                print(f"   Lead {id}: {nombre}, tel={telefono}, status1='{status1}', status2='{status2}', lead_status='{lead_status}', origen='{origen}', seleccionado={selected_str}")
        else:
            print("   No se encontraron leads que cumplan los criterios")

        print()

        # PASO 5: Verificar problema con encoding o espacios
        print("5. VERIFICACION DE PROBLEMAS DE FORMATO:")

        # Verificar valores exactos de status_level_1
        cursor.execute("SELECT DISTINCT status_level_1, COUNT(*) as count FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO' GROUP BY status_level_1 ORDER BY count DESC LIMIT 10")
        status_values = cursor.fetchall()
        print("   Valores unicos de status_level_1 en SEGURCAIXA_JULIO:")
        for status, count in status_values:
            status_repr = repr(status) if status else 'NULL'
            print(f"     {status_repr}: {count} leads")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    verificar_consulta_call_manager()
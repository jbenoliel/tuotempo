#!/usr/bin/env python3
"""
Analiza el patrón exacto de generación de call_ids inválidos
"""

import mysql.connector
from dotenv import load_dotenv
import binascii

load_dotenv()

def get_railway_connection():
    config = {
        'host': 'ballast.proxy.rlwy.net',
        'port': 11616,
        'user': 'root',
        'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        'database': 'railway',
        'ssl_disabled': True,
        'autocommit': True,
        'charset': 'utf8mb4'
    }
    try:
        return mysql.connector.connect(**config)
    except Exception as e:
        print(f"Error: {e}")
        return None

def analizar_patron_generacion():
    conn = get_railway_connection()
    if not conn:
        return

    cursor = conn.cursor()

    print("ANÁLISIS DETALLADO DE PATRONES CALL_ID")
    print("=" * 60)

    # 1. Analizar call_ids inválidos generados HOY
    print("\n1. CALL_IDS INVÁLIDOS DE HOY:")
    cursor.execute("""
        SELECT call_id, created_at, lead_id,
               SUBSTRING(call_id, 1, 6) as prefijo_6,
               SUBSTRING(call_id, 7, 8) as middle_8,
               SUBSTRING(call_id, 15) as suffix
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        AND DATE(created_at) = '2025-09-17'
        ORDER BY created_at
        LIMIT 20
    """)

    invalidos_hoy = cursor.fetchall()

    print(f"{'CALL_ID':<30} {'PREFIJO':<8} {'MIDDLE':<10} {'SUFFIX':<15} {'LEAD_ID':<8}")
    print("-" * 75)

    prefijos = {}
    for call_id, created, lead_id, prefijo, middle, suffix in invalidos_hoy:
        print(f"{call_id:<30} {prefijo:<8} {middle:<10} {suffix:<15} {lead_id:<8}")

        # Contar prefijos
        if prefijo not in prefijos:
            prefijos[prefijo] = 0
        prefijos[prefijo] += 1

    print(f"\nPREFIJOS MÁS COMUNES:")
    for prefijo, count in sorted(prefijos.items(), key=lambda x: x[1], reverse=True):
        print(f"  {prefijo}: {count} call_ids")

    # 2. Comparar con call_ids válidos
    print("\n2. CALL_IDS VÁLIDOS PARA COMPARACIÓN:")
    cursor.execute("""
        SELECT call_id, created_at,
               SUBSTRING(call_id, 1, 6) as prefijo_6,
               SUBSTRING(call_id, 7, 8) as middle_8,
               SUBSTRING(call_id, 15) as suffix
        FROM pearl_calls
        WHERE summary IS NOT NULL
        AND summary != ''
        AND summary != 'Call_id invalido - no reconocido por Pearl AI'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    validos = cursor.fetchall()

    print(f"{'CALL_ID':<30} {'PREFIJO':<8} {'MIDDLE':<10} {'SUFFIX'}")
    print("-" * 65)

    prefijos_validos = {}
    for call_id, created, prefijo, middle, suffix in validos:
        print(f"{call_id:<30} {prefijo:<8} {middle:<10} {suffix}")

        if prefijo not in prefijos_validos:
            prefijos_validos[prefijo] = 0
        prefijos_validos[prefijo] += 1

    print(f"\nPREFIJOS VÁLIDOS:")
    for prefijo, count in sorted(prefijos_validos.items(), key=lambda x: x[1], reverse=True):
        print(f"  {prefijo}: {count} call_ids")

    # 3. Análisis temporal - buscar el momento exacto de generación
    print("\n3. ANÁLISIS TEMPORAL DE GENERACIÓN:")
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') as minuto,
               COUNT(*) as cantidad_generada
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        AND DATE(created_at) = '2025-09-17'
        GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d %H:%i')
        ORDER BY minuto
    """)

    temporal = cursor.fetchall()

    print("MOMENTO DE GENERACIÓN:")
    for minuto, cantidad in temporal:
        print(f"  {minuto}: {cantidad} call_ids generados")

    # 4. Verificar si hay secuencia numérica
    print("\n4. ANÁLISIS DE SECUENCIA NUMÉRICA:")
    cursor.execute("""
        SELECT call_id, created_at, lead_id
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        AND DATE(created_at) = '2025-09-17'
        ORDER BY created_at, id
        LIMIT 10
    """)

    secuencia = cursor.fetchall()

    print("PRIMEROS 10 CALL_IDS EN SECUENCIA:")
    for i, (call_id, created, lead_id) in enumerate(secuencia):
        print(f"  {i+1:2d}. {call_id} (Lead: {lead_id}) - {created}")

        # Intentar convertir parte del call_id a número para ver patrón
        try:
            # Los últimos caracteres podrían ser secuenciales
            suffix_hex = call_id[-8:]  # Últimos 8 caracteres
            suffix_decimal = int(suffix_hex, 16)
            print(f"      Sufijo hex: {suffix_hex} = decimal: {suffix_decimal}")
        except:
            pass

    # 5. Buscar leads asociados a estos call_ids
    print("\n5. LEADS ASOCIADOS A CALL_IDS INVÁLIDOS:")
    cursor.execute("""
        SELECT pc.lead_id, l.nombre, l.telefono, l.call_status,
               COUNT(pc.call_id) as num_call_ids_invalidos
        FROM pearl_calls pc
        LEFT JOIN leads l ON pc.lead_id = l.id
        WHERE pc.status = 'invalid_call_id'
        AND DATE(pc.created_at) = '2025-09-17'
        GROUP BY pc.lead_id, l.nombre, l.telefono, l.call_status
        ORDER BY num_call_ids_invalidos DESC
        LIMIT 10
    """)

    leads_afectados = cursor.fetchall()

    print(f"{'LEAD_ID':<8} {'NOMBRE':<20} {'TELÉFONO':<12} {'STATUS':<12} {'#CALL_IDS'}")
    print("-" * 65)

    for lead_id, nombre, telefono, call_status, num_calls in leads_afectados:
        nombre_short = (nombre[:17] + '...') if nombre and len(nombre) > 20 else (nombre or 'N/A')
        print(f"{lead_id:<8} {nombre_short:<20} {telefono:<12} {call_status:<12} {num_calls}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    analizar_patron_generacion()
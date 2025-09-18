#!/usr/bin/env python3
"""
Investigar el origen de los call_ids invalidos
"""

import mysql.connector
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

def investigar_origen_invalidos():
    conn = get_railway_connection()
    if not conn:
        return

    cursor = conn.cursor()

    print("INVESTIGACIÓN DE CALL_IDS INVÁLIDOS")
    print("=" * 60)

    # 1. Analizar patrones de call_ids inválidos
    print("\n1. PATRONES DE CALL_IDS INVÁLIDOS:")
    cursor.execute("""
        SELECT call_id, created_at, updated_at,
               TIMESTAMPDIFF(MINUTE, created_at, updated_at) as minutos_hasta_invalido
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    invalidos = cursor.fetchall()
    print(f"{'CALL_ID':<30} {'CREADO':<20} {'INVALIDADO':<20} {'MIN'}")
    print("-" * 80)
    for row in invalidos:
        call_id, created, updated, minutes = row
        created_str = created.strftime('%Y-%m-%d %H:%M') if created else 'N/A'
        updated_str = updated.strftime('%Y-%m-%d %H:%M') if updated else 'N/A'
        print(f"{call_id:<30} {created_str:<20} {updated_str:<20} {minutes}")

    # 2. Distribución por fechas
    print("\n2. DISTRIBUCIÓN POR FECHAS:")
    cursor.execute("""
        SELECT DATE(created_at) as fecha,
               COUNT(*) as total_invalidos
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        GROUP BY DATE(created_at)
        ORDER BY fecha DESC
        LIMIT 7
    """)

    fechas = cursor.fetchall()
    for fecha, count in fechas:
        print(f"  {fecha}: {count} call_ids inválidos")

    # 3. Comparar con call_ids válidos del mismo período
    print("\n3. COMPARACIÓN CON VÁLIDOS DEL MISMO PERÍODO:")
    cursor.execute("""
        SELECT
            status,
            COUNT(*) as cantidad,
            MIN(created_at) as primer_registro,
            MAX(created_at) as ultimo_registro
        FROM pearl_calls
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY status
        ORDER BY cantidad DESC
    """)

    comparacion = cursor.fetchall()
    print(f"{'STATUS':<20} {'CANTIDAD':<10} {'PRIMER REGISTRO':<20} {'ÚLTIMO REGISTRO'}")
    print("-" * 70)
    for status, cantidad, primer, ultimo in comparacion:
        primer_str = primer.strftime('%Y-%m-%d %H:%M') if primer else 'N/A'
        ultimo_str = ultimo.strftime('%Y-%m-%d %H:%M') if ultimo else 'N/A'
        print(f"{status:<20} {cantidad:<10} {primer_str:<20} {ultimo_str}")

    # 4. Analizar leads asociados a call_ids inválidos
    print("\n4. LEADS ASOCIADOS A CALL_IDS INVÁLIDOS:")
    cursor.execute("""
        SELECT l.id, l.nombre, l.telefono, l.call_status, pc.call_id, pc.created_at
        FROM pearl_calls pc
        JOIN leads l ON pc.lead_id = l.id
        WHERE pc.status = 'invalid_call_id'
        ORDER BY pc.created_at DESC
        LIMIT 5
    """)

    leads_invalidos = cursor.fetchall()
    print(f"{'LEAD_ID':<8} {'NOMBRE':<20} {'TELÉFONO':<12} {'CALL_STATUS':<15} {'CALL_ID':<25}")
    print("-" * 90)
    for lead_id, nombre, telefono, call_status, call_id, created in leads_invalidos:
        nombre_short = (nombre[:17] + '...') if nombre and len(nombre) > 20 else (nombre or 'N/A')
        print(f"{lead_id:<8} {nombre_short:<20} {telefono:<12} {call_status:<15} {call_id[:22]+'...'}")

    # 5. Verificar si hay patrones en los call_ids inválidos
    print("\n5. ANÁLISIS DE PATRONES EN CALL_IDS:")
    cursor.execute("""
        SELECT
            LEFT(call_id, 8) as prefijo,
            COUNT(*) as cantidad
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        GROUP BY LEFT(call_id, 8)
        ORDER BY cantidad DESC
        LIMIT 10
    """)

    prefijos = cursor.fetchall()
    print("Prefijos más comunes en call_ids inválidos:")
    for prefijo, cantidad in prefijos:
        print(f"  {prefijo}*: {cantidad} call_ids")

    # 6. Verificar si los call_ids válidos tienen patrones diferentes
    print("\n6. COMPARACIÓN CON PREFIJOS DE CALL_IDS VÁLIDOS:")
    cursor.execute("""
        SELECT
            LEFT(call_id, 8) as prefijo,
            COUNT(*) as cantidad
        FROM pearl_calls
        WHERE summary IS NOT NULL
        AND summary != ''
        AND summary != 'Call_id invalido - no reconocido por Pearl AI'
        GROUP BY LEFT(call_id, 8)
        ORDER BY cantidad DESC
        LIMIT 5
    """)

    prefijos_validos = cursor.fetchall()
    print("Prefijos más comunes en call_ids VÁLIDOS:")
    for prefijo, cantidad in prefijos_validos:
        print(f"  {prefijo}*: {cantidad} call_ids")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    investigar_origen_invalidos()
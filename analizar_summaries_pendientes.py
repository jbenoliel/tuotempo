#!/usr/bin/env python3
"""
Analiza por que no se estan recuperando mas summaries
"""

import pymysql
from datetime import datetime
from pearl_caller import get_pearl_client

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

def analizar_pendientes():
    """Analiza los registros pendientes para entender el problema"""

    print("=== ANALISIS SUMMARIES PENDIENTES ===")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Estado general
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        con_summary = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE status = '4'")
        total_status_4 = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
        """)
        pendientes = cursor.fetchone()[0]

        print("ESTADO GENERAL:")
        print(f"  Total llamadas completadas (status=4): {total_status_4}")
        print(f"  Summaries recuperados: {con_summary}")
        print(f"  Pendientes: {pendientes}")
        print(f"  Porcentaje: {con_summary/total_status_4*100:.1f}%")
        print()

        # 2. Analizar distribución por fechas
        print("DISTRIBUCIÓN POR FECHAS (pendientes):")
        cursor.execute("""
            SELECT DATE(created_at) as fecha, COUNT(*) as count
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
            GROUP BY DATE(created_at)
            ORDER BY fecha DESC
            LIMIT 10
        """)
        por_fechas = cursor.fetchall()

        for fecha, count in por_fechas:
            print(f"  {fecha}: {count} pendientes")

        print()

        # 3. Probar algunos call_ids pendientes recientes
        print("PROBANDO CALL_IDS PENDIENTES RECIENTES:")
        cursor.execute("""
            SELECT id, call_id, lead_id, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        ejemplos_recientes = cursor.fetchall()

        client = get_pearl_client()

        for id_reg, call_id, lead_id, created_at in ejemplos_recientes:
            print(f"  Call ID: {call_id} (Lead {lead_id}, {created_at})")

            try:
                call_details = client.get_call_status(call_id)

                if call_details:
                    summary = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')

                    if summary and summary.strip():
                        print(f"    [TIENE SUMMARY] {len(summary)} caracteres")
                        print(f"    Preview: {summary[:80]}...")
                    else:
                        print(f"    [SIN SUMMARY] Pearl no tiene summary para este call_id")

                    # Mostrar otros campos disponibles
                    campos = ['status', 'duration', 'conversationStatus', 'startTime']
                    info = []
                    for campo in campos:
                        if campo in call_details:
                            info.append(f"{campo}={call_details[campo]}")
                    if info:
                        print(f"    Datos: {', '.join(info)}")

                else:
                    print(f"    [ERROR] No se pudo obtener información de Pearl")

            except Exception as e:
                print(f"    [ERROR] {e}")

            print()

        # 4. Probar algunos antiguos también
        print("PROBANDO CALL_IDS PENDIENTES ANTIGUOS:")
        cursor.execute("""
            SELECT id, call_id, lead_id, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
            ORDER BY created_at ASC
            LIMIT 3
        """)
        ejemplos_antiguos = cursor.fetchall()

        for id_reg, call_id, lead_id, created_at in ejemplos_antiguos:
            print(f"  Call ID: {call_id} (Lead {lead_id}, {created_at})")

            try:
                call_details = client.get_call_status(call_id)

                if call_details:
                    summary = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')

                    if summary and summary.strip():
                        print(f"    [TIENE SUMMARY] {len(summary)} caracteres - ¿Por qué no se recuperó?")
                    else:
                        print(f"    [SIN SUMMARY] Pearl no generó summary para esta llamada antigua")
                else:
                    print(f"    [ERROR] Call_id no existe en Pearl")

            except Exception as e:
                print(f"    [ERROR] {e}")

            print()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analizar_pendientes()
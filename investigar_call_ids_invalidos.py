#!/usr/bin/env python3
"""
Investiga los call_ids que estan dando 'wrong CallId' en Pearl AI
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

def investigar_call_ids_invalidos():
    """Investiga los call_ids problematicos y su contexto"""

    print("=== INVESTIGACION CALL_IDS INVALIDOS ===")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Examinar los call_ids problematicos
        call_ids_problema = [
            "68c942494d6fa815eed12668",
            "68c9424af8275e862ff7bd14",
            "68c9424a4d6fa815eed12669"
        ]

        print("ANALISIS CALL_IDS PROBLEMATICOS:")
        for call_id in call_ids_problema:
            print(f"\n  Call ID: {call_id}")

            # Buscar el registro completo
            cursor.execute("""
                SELECT id, call_id, phone_number, lead_id, outbound_id,
                       status, call_time, duration, summary, created_at, updated_at
                FROM pearl_calls
                WHERE call_id = %s
            """, [call_id])

            registro = cursor.fetchone()
            if registro:
                id_reg, call_id_db, phone, lead_id, outbound_id, status, call_time, duration, summary, created_at, updated_at = registro
                print(f"    ID: {id_reg}")
                print(f"    Phone: {phone}")
                print(f"    Lead ID: {lead_id}")
                print(f"    Outbound ID: {outbound_id}")
                print(f"    Status: {status}")
                print(f"    Call Time: {call_time}")
                print(f"    Created: {created_at}")
                print(f"    Updated: {updated_at}")
                print(f"    Summary: {'Si' if summary else 'No'}")
                print(f"    Duration: {duration}")

                # Buscar el lead correspondiente
                cursor.execute("""
                    SELECT id, nombre, telefono, call_status, last_call_attempt, call_attempts_count
                    FROM leads
                    WHERE id = %s
                """, [lead_id])

                lead = cursor.fetchone()
                if lead:
                    lead_id_db, nombre, telefono, call_status, last_attempt, attempts = lead
                    print(f"    Lead: {nombre} ({telefono})")
                    print(f"    Lead Status: {call_status}")
                    print(f"    Last Attempt: {last_attempt}")
                    print(f"    Attempts Count: {attempts}")

        # 2. Verificar el patron temporal de estas llamadas
        print("\n\nPATRON TEMPORAL:")
        cursor.execute("""
            SELECT DATE_FORMAT(created_at, '%H:%i:%s') as hora_creacion,
                   COUNT(*) as cantidad,
                   GROUP_CONCAT(call_id SEPARATOR ', ') as call_ids
            FROM pearl_calls
            WHERE created_at >= '2025-09-16 10:56:00'
            AND created_at <= '2025-09-16 10:57:00'
            AND call_id IS NOT NULL
            GROUP BY DATE_FORMAT(created_at, '%H:%i:%s')
            ORDER BY hora_creacion
        """)

        patron_temporal = cursor.fetchall()
        for hora, cantidad, call_ids_list in patron_temporal:
            print(f"  {hora}: {cantidad} llamadas - {call_ids_list}")

        # 3. Verificar si hay otros call_ids de la misma epoca que SI funcionan
        print("\n\nCALL_IDS EXITOSOS DE LA MISMA EPOCA:")
        cursor.execute("""
            SELECT call_id, summary IS NOT NULL as tiene_summary
            FROM pearl_calls
            WHERE created_at >= '2025-09-16 10:55:00'
            AND created_at <= '2025-09-16 11:00:00'
            AND call_id IS NOT NULL
            AND call_id NOT IN ('68c942494d6fa815eed12668', '68c9424af8275e862ff7bd14', '68c9424a4d6fa815eed12669')
            LIMIT 5
        """)

        exitosos = cursor.fetchall()
        if exitosos:
            print("  Call_ids de la misma epoca que podrian funcionar:")
            for call_id_ok, tiene_summary in exitosos:
                status_summary = "Con summary" if tiene_summary else "Sin summary"
                print(f"    {call_id_ok} ({status_summary})")
        else:
            print("  No hay otros call_ids de esa epoca")

        # 4. Recomendacion
        print("\n\nRECOMENDACION:")
        print("  Estos call_ids parecen ser invalidos desde el origen.")
        print("  Posibles causas:")
        print("    - Timeout durante la creacion de la llamada")
        print("    - Error en la respuesta de Pearl AI")
        print("    - Call_ids corruptos o incompletos")
        print("  ")
        print("  ACCION SUGERIDA:")
        print("    - Marcar estos registros como error permanente")
        print("    - No volver a intentar procesarlos")
        print("    - Crear mecanismo para detectar call_ids invalidos")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    investigar_call_ids_invalidos()
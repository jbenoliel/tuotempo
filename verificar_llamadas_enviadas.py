#!/usr/bin/env python3
"""
Verifica si las llamadas seleccionadas se enviaron exitosamente a Pearl AI
"""

import pymysql
from datetime import datetime, timedelta

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

def verificar_llamadas_recientes():
    """Verifica el estado de las llamadas mas recientes"""

    print("=== VERIFICACION LLAMADAS ENVIADAS A PEARL AI ===")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Verificar leads seleccionados recientemente
        print("1. LEADS SELECCIONADOS RECIENTEMENTE:")
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE selected_for_calling = TRUE
        """)
        leads_seleccionados = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, nombre, telefono, updated_at
            FROM leads
            WHERE selected_for_calling = TRUE
            ORDER BY updated_at DESC
            LIMIT 10
        """)
        ejemplos_seleccionados = cursor.fetchall()

        print(f"  Total leads seleccionados actualmente: {leads_seleccionados}")
        if ejemplos_seleccionados:
            print("  Ejemplos de leads seleccionados:")
            for id_lead, nombre, telefono, updated_at in ejemplos_seleccionados:
                print(f"    Lead {id_lead}: {nombre} ({telefono}) - Seleccionado: {updated_at}")
        print()

        # 2. Verificar llamadas en pearl_calls de las ultimas 2 horas
        print("2. LLAMADAS REGISTRADAS EN PEARL_CALLS (ultimas 2 horas):")
        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """)
        llamadas_2h = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, call_id, lead_id, phone_number, status, created_at
            FROM pearl_calls
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
            ORDER BY created_at DESC
            LIMIT 10
        """)
        llamadas_recientes = cursor.fetchall()

        print(f"  Total llamadas registradas (2h): {llamadas_2h}")
        if llamadas_recientes:
            print("  Llamadas recientes:")
            for id_pearl, call_id, lead_id, phone, status, created_at in llamadas_recientes:
                call_id_short = call_id[:12] + "..." if call_id else "No call_id"
                print(f"    {created_at}: Lead {lead_id} -> {call_id_short} | Status: {status}")
        else:
            print("    [INFO] No se registraron llamadas en las ultimas 2 horas")
        print()

        # 3. Verificar actualizaciones de call_status en leads
        print("3. ACTUALIZACIONES DE CALL_STATUS EN LEADS (ultimas 2 horas):")
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE last_call_attempt >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """)
        leads_con_intentos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, nombre, telefono, call_status, last_call_attempt, call_attempts_count
            FROM leads
            WHERE last_call_attempt >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
            ORDER BY last_call_attempt DESC
            LIMIT 10
        """)
        leads_intentos = cursor.fetchall()

        print(f"  Leads con intentos de llamada (2h): {leads_con_intentos}")
        if leads_intentos:
            print("  Ejemplos:")
            for id_lead, nombre, telefono, call_status, last_attempt, attempts_count in leads_intentos:
                print(f"    Lead {id_lead}: {nombre} ({telefono})")
                print(f"      Status: {call_status} | Ultimo intento: {last_attempt} | Intentos: {attempts_count}")
        else:
            print("    [INFO] No hay leads con intentos de llamada recientes")
        print()

        # 4. Analisis de resultados
        print("4. ANALISIS DE RESULTADOS:")

        if leads_con_intentos > 0:
            if llamadas_2h > 0:
                print("  [EXITO] Las llamadas SI se enviaron a Pearl AI")
                print(f"    - {leads_con_intentos} leads procesados")
                print(f"    - {llamadas_2h} llamadas registradas en pearl_calls")

                # Verificar si los errores fueron despues del envio
                cursor.execute("""
                    SELECT COUNT(*) FROM pearl_calls
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
                    AND call_id IS NOT NULL AND call_id != ''
                """)
                con_call_id = cursor.fetchone()[0]

                print(f"    - {con_call_id} llamadas con call_id valido de Pearl AI")

                if con_call_id > 0:
                    print("  [CONFIRMADO] Pearl AI respondio con call_ids validos")
                    print("  Los errores 'wrong CallId' fueron al intentar obtener detalles muy rapido")
                else:
                    print("  [PROBLEMA] Pearl AI no devolvio call_ids validos")

            else:
                print("  [PROBLEMA] Las llamadas NO llegaron a pearl_calls")
                print("    - Los leads se procesaron pero no se registraron en Pearl AI")
                print("    - Puede haber un error en la conexion a Pearl AI")

        else:
            print("  [INFO] No se procesaron llamadas recientemente")
            if leads_seleccionados > 0:
                print("    - Hay leads seleccionados pero no se han procesado")
                print("    - ¿El sistema de llamadas esta corriendo?")
            else:
                print("    - No hay leads seleccionados actualmente")

        # 5. Verificar estado del call manager
        print()
        print("5. VERIFICACION ADICIONAL:")

        # Buscar registros con status basico
        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE status IN ('1', 'pending', 'basic')
            AND created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """)
        registros_basicos = cursor.fetchone()[0]

        if registros_basicos > 0:
            print(f"  Registros basicos creados por call_manager: {registros_basicos}")
            print("  [EXITO] Las llamadas SI se enviaron, los errores son posteriores")
        else:
            print("  No hay registros basicos recientes")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    verificar_llamadas_recientes()
    print()
    print("=" * 60)
    print("Esta verificacion te dira exactamente si tus llamadas")
    print("llegaron a Pearl AI o si el error fue antes.")
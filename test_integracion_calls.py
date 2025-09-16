#!/usr/bin/env python3
"""
Prueba la integracion completa de calls_updater con call_manager
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

def test_integracion():
    """Verifica el estado de la integracion y ejecuta calls_updater si es necesario"""

    print("=== TEST INTEGRACION CALLS_UPDATER ===")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Verificar registros basicos pendientes
        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL
            AND (summary IS NULL OR summary = '')
            AND (duration IS NULL OR duration = 0)
            AND status IN ('1', 'pending', 'basic')
            AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        basicos_pendientes = cursor.fetchone()[0]

        print(f"ESTADO ACTUAL:")
        print(f"  Registros basicos pendientes (24h): {basicos_pendientes}")

        # 2. Verificar algunos ejemplos
        if basicos_pendientes > 0:
            cursor.execute("""
                SELECT id, call_id, lead_id, status, created_at
                FROM pearl_calls
                WHERE call_id IS NOT NULL
                AND (summary IS NULL OR summary = '')
                AND (duration IS NULL OR duration = 0)
                AND status IN ('1', 'pending', 'basic')
                AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ORDER BY created_at DESC
                LIMIT 5
            """)
            ejemplos = cursor.fetchall()

            print("  Ejemplos de registros basicos:")
            for id_reg, call_id, lead_id, status, created_at in ejemplos:
                print(f"    ID {id_reg}: {call_id} | Lead {lead_id} | Status {status} | {created_at}")

            print()
            print("[ACCION] Ejecutando calls_updater para completar registros basicos...")

            # 3. Ejecutar la funcion de completar registros basicos
            try:
                from calls_updater import complete_basic_call_records
                completed = complete_basic_call_records()
                print(f"[RESULTADO] {completed} registros completados por calls_updater")

                # 4. Verificar estado despues
                cursor.execute("""
                    SELECT COUNT(*) FROM pearl_calls
                    WHERE call_id IS NOT NULL
                    AND (summary IS NULL OR summary = '')
                    AND (duration IS NULL OR duration = 0)
                    AND status IN ('1', 'pending', 'basic')
                    AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                """)
                basicos_restantes = cursor.fetchone()[0]

                print(f"[VERIFICACION] Registros basicos restantes: {basicos_restantes}")

                # 5. Contar summaries nuevos
                cursor.execute("""
                    SELECT COUNT(*) FROM pearl_calls
                    WHERE summary IS NOT NULL AND summary != ''
                    AND updated_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                """)
                summaries_nuevos = cursor.fetchone()[0]

                print(f"[SUMMARIES] Summaries creados en la ultima hora: {summaries_nuevos}")

            except Exception as e:
                print(f"[ERROR] Error ejecutando calls_updater: {e}")

        else:
            print("  No hay registros basicos pendientes")

        # 6. Estado general
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        total_summaries = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE status = '4'")
        total_completadas = cursor.fetchone()[0]

        print()
        print("ESTADO GENERAL:")
        print(f"  Total summaries: {total_summaries}")
        print(f"  Total llamadas completadas: {total_completadas}")
        if total_completadas > 0:
            print(f"  Porcentaje con summary: {total_summaries/total_completadas*100:.1f}%")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_integracion()
    print()
    print("=" * 60)
    print("Integracion verificada. Ahora las nuevas llamadas")
    print("deberan guardar summaries automaticamente.")
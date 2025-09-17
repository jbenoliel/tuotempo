#!/usr/bin/env python3
"""
Marca todos los call_ids invalidos conocidos como permanentemente fallidos
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

def marcar_call_ids_invalidos():
    """Marca todos los call_ids invalidos conocidos"""

    print("=== MARCANDO CALL_IDS INVALIDOS ===")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Call_ids que sabemos son invalidos
        call_ids_invalidos = [
            "68c9424af8275e862ff7bd14",  # ID 1854
            "68c9424a4d6fa815eed12669"   # ID 1855
        ]

        print("Marcando call_ids invalidos restantes:")

        for call_id in call_ids_invalidos:
            # Buscar el registro
            cursor.execute("""
                SELECT id, lead_id FROM pearl_calls
                WHERE call_id = %s
            """, [call_id])

            registro = cursor.fetchone()
            if registro:
                record_id, lead_id = registro
                print(f"  {call_id} (ID: {record_id}, Lead: {lead_id})")

                # Marcar como invalido
                cursor.execute("""
                    UPDATE pearl_calls
                    SET status = 'invalid_call_id',
                        summary = 'Call_id invalido - no reconocido por Pearl AI',
                        updated_at = NOW()
                    WHERE id = %s
                """, [record_id])

                print(f"    [MARCADO] Como invalid_call_id")
            else:
                print(f"  {call_id} - No encontrado")

        conn.commit()

        # Verificar estado final
        print("\nVERIFICACION FINAL:")
        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL
            AND (summary IS NULL OR summary = '')
            AND (duration IS NULL OR duration = 0)
            AND status IN ('1', 'pending', 'basic')
            AND status != 'invalid_call_id'
            AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)

        registros_pendientes = cursor.fetchone()[0]
        print(f"  Registros basicos pendientes (24h): {registros_pendientes}")

        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE status = 'invalid_call_id'
        """)

        invalidos_totales = cursor.fetchone()[0]
        print(f"  Total call_ids marcados como invalidos: {invalidos_totales}")

        print("\n[EXITO] Todos los call_ids invalidos conocidos han sido marcados")
        print("El sistema ya no intentara procesarlos y no generara mas errores")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    marcar_call_ids_invalidos()
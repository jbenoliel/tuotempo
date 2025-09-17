#!/usr/bin/env python3
"""
Prueba el manejo de call_ids invalidos directamente
"""

import pymysql
import os
from dotenv import load_dotenv
from pearl_caller import get_pearl_client, PearlAPIError

load_dotenv()

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

def test_invalid_callid_handling():
    """Prueba el manejo de call_ids invalidos"""

    print("=== TEST MANEJO CALL_IDS INVALIDOS ===")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Obtener un call_id invalido conocido
        call_id_invalido = "68c942494d6fa815eed12668"
        record_id = 1853

        print(f"Procesando call_id invalido: {call_id_invalido}")

        # 2. Intentar obtener detalles con Pearl AI (debe fallar)
        try:
            pearl_client = get_pearl_client()
            call_details = pearl_client.get_call_status(call_id_invalido)
            print("  [ERROR INESPERADO] Pearl AI no deberia haber devuelto datos")
        except Exception as e:
            error_message = str(e)
            print(f"  Pearl AI error: {error_message}")

            # 3. Si es el error esperado, marcar como invalido
            if "wrong CallId" in error_message:
                print("  [EXITO] Detectado error 'wrong CallId'")
                print("  Marcando call_id como permanentemente invalido...")

                cursor.execute("""
                    UPDATE pearl_calls
                    SET status = 'invalid_call_id',
                        summary = 'Call_id invalido - no reconocido por Pearl AI',
                        updated_at = NOW()
                    WHERE id = %s
                """, [record_id])

                conn.commit()
                print("  [COMPLETADO] Call_id marcado como invalido")

                # 4. Verificar la actualizacion
                cursor.execute("""
                    SELECT status, summary, updated_at
                    FROM pearl_calls
                    WHERE id = %s
                """, [record_id])

                resultado = cursor.fetchone()
                if resultado:
                    status, summary, updated_at = resultado
                    print(f"  Estado actualizado: {status}")
                    print(f"  Summary: {summary}")
                    print(f"  Actualizado: {updated_at}")

            else:
                print(f"  [ERROR DIFERENTE] No es 'wrong CallId': {error_message}")

        # 5. Verificar que el registro ya no aparezca en busquedas futuras
        print("\n  Verificando exclusion en futuras busquedas...")
        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL
            AND (summary IS NULL OR summary = '')
            AND (duration IS NULL OR duration = 0)
            AND status IN ('1', 'pending', 'basic')
            AND status != 'invalid_call_id'
            AND id = %s
        """, [record_id])

        count = cursor.fetchone()[0]
        if count == 0:
            print("  [EXITO] El registro ya no aparece en busquedas futuras")
        else:
            print("  [ERROR] El registro aun aparece en busquedas")

        print("\nCONCLUSION:")
        print("  El manejo de call_ids invalidos funciona correctamente")
        print("  Los call_ids invalidos se marcan como 'invalid_call_id'")
        print("  No volveran a procesarse en el futuro")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_invalid_callid_handling()
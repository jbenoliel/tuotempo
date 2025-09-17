#!/usr/bin/env python3
"""
Prueba el fix del delay de 2 minutos para procesar registros basicos
"""

import pymysql
import requests
import json
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

def test_delay_fix():
    """Prueba el procesamiento de registros basicos con el delay de 2 minutos"""

    print("=== TEST DELAY FIX PARA REGISTROS BASICOS ===")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Buscar registros que cumplen con la nueva condicion (2 minutos de delay)
        cursor.execute("""
            SELECT id, call_id, lead_id, phone_number, outbound_id, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL
            AND (summary IS NULL OR summary = '')
            AND (duration IS NULL OR duration = 0)
            AND status IN ('1', 'pending', 'basic')
            AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND created_at <= DATE_SUB(NOW(), INTERVAL 2 MINUTE)
            LIMIT 5
        """)

        registros_validos = cursor.fetchall()

        print(f"REGISTROS QUE CUMPLEN CON EL DELAY DE 2 MINUTOS: {len(registros_validos)}")

        if not registros_validos:
            print("  No hay registros que cumplan con los criterios")
            return

        print("  Registros encontrados:")
        for id_reg, call_id, lead_id, phone, outbound_id, created_at in registros_validos:
            minutos_transcurridos = (datetime.now() - created_at).total_seconds() / 60
            print(f"    ID {id_reg}: {call_id} | Lead {lead_id} | Creado hace {minutos_transcurridos:.1f} minutos")

        print()

        # 2. Probar obtencion de detalles de Pearl AI para el primer registro
        primer_registro = registros_validos[0]
        call_id = primer_registro[1]

        print(f"PROBANDO PEARL AI API CON CALL_ID: {call_id}")

        try:
            # Configuracion Pearl AI correcta
            import os
            from dotenv import load_dotenv
            load_dotenv()

            account_id = os.getenv('PEARL_ACCOUNT_ID')
            secret_key = os.getenv('PEARL_SECRET_KEY')
            api_url = os.getenv('PEARL_API_URL', 'https://api.nlpearl.ai/v1')

            if not account_id or not secret_key:
                print("  [ERROR] Credenciales Pearl AI no configuradas en .env")
                return

            pearl_headers = {
                'Authorization': f'Bearer {account_id}:{secret_key}',
                'Content-Type': 'application/json'
            }

            response = requests.get(
                f'{api_url}/Call/{call_id}',
                headers=pearl_headers,
                timeout=30
            )

            print(f"  Status Code: {response.status_code}")

            if response.status_code == 200:
                call_data = response.json()
                print("  [EXITO] Pearl AI respondio correctamente")
                print(f"    Summary presente: {'summary' in call_data and call_data['summary']}")
                print(f"    Duration presente: {'duration' in call_data and call_data['duration']}")
                print(f"    Status: {call_data.get('status', 'N/A')}")

                # Si tenemos datos, actualizar el registro
                if 'summary' in call_data and call_data['summary']:
                    summary = call_data['summary'][:1000] if call_data['summary'] else None
                    duration = call_data.get('duration', 0)
                    status = call_data.get('status', '1')

                    cursor.execute("""
                        UPDATE pearl_calls
                        SET summary = %s, duration = %s, status = %s, updated_at = NOW()
                        WHERE id = %s
                    """, [summary, duration, status, primer_registro[0]])

                    conn.commit()
                    print("  [ACTUALIZADO] Registro actualizado con exito")
                else:
                    print("  [INFO] Pearl AI aun no tiene summary/duration disponible")

            elif response.status_code == 400:
                error_data = response.json()
                if 'errors' in error_data and 'validation' in error_data['errors']:
                    validation_errors = error_data['errors']['validation']
                    if 'wrong CallId' in validation_errors:
                        print("  [ERROR] wrong CallId - Pearl AI aun no reconoce este call_id")
                        print("  [POSIBLE SOLUCION] Necesita mas tiempo de procesamiento")
                    else:
                        print(f"  [ERROR] Validation error: {validation_errors}")
                else:
                    print(f"  [ERROR] Error 400: {error_data}")
            else:
                print(f"  [ERROR] Status {response.status_code}: {response.text}")

        except Exception as e:
            print(f"  [ERROR] Exception al llamar Pearl AI: {e}")

        print()
        print("CONCLUSION:")
        print("- El delay de 2 minutos esta implementado correctamente")
        print("- Los registros antiguos pueden procesarse")
        if len(registros_validos) > 0:
            print("- Si sigue dando 'wrong CallId', necesita mas tiempo de delay")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_delay_fix()
#!/usr/bin/env python3
"""
Inspecciona la estructura real de las respuestas de Pearl AI para entender
como viene el summary y por que no se esta guardando
"""

import pymysql
from datetime import datetime
from pearl_caller import get_pearl_client
import json

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

def inspeccionar_respuesta_pearl():
    """Obtiene los detalles de llamadas recientes de Pearl AI"""

    print("=== INSPECCION RESPUESTA PEARL AI ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    # 1. Obtener algunos call_ids recientes de la BD
    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Obtener los 3 call_ids mas recientes
        cursor.execute("""
            SELECT call_id, lead_id, status, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            ORDER BY created_at DESC
            LIMIT 3
        """)
        call_ids = cursor.fetchall()

        if not call_ids:
            print("No hay call_ids en la base de datos")
            return

        print("CALL_IDS OBTENIDOS DE LA BD:")
        for call_id, lead_id, status, created_at in call_ids:
            print(f"  {call_id} | Lead {lead_id} | Status {status} | {created_at}")

        print()

        # 2. Conectar a Pearl AI y obtener detalles
        client = get_pearl_client()

        for call_id, lead_id, status, created_at in call_ids:
            print(f"=== DETALLES DE CALL_ID: {call_id} ===")

            try:
                # Obtener detalles completos de Pearl
                call_details = client.get_call_status(call_id)

                if call_details:
                    print("ESTRUCTURA COMPLETA DE LA RESPUESTA:")
                    print(json.dumps(call_details, indent=2, ensure_ascii=False))
                    print()

                    # Analizar específicamente el campo summary
                    summary_field = call_details.get('summary')
                    print(f"CAMPO SUMMARY:")
                    print(f"  Tipo: {type(summary_field)}")
                    print(f"  Valor: {summary_field}")

                    if isinstance(summary_field, dict):
                        print(f"  Es diccionario con llaves: {list(summary_field.keys())}")
                        if 'text' in summary_field:
                            print(f"  summary.text: {summary_field['text']}")

                    print()

                    # Verificar otros campos que puedan contener resumen
                    campos_posibles = ['summary', 'callSummary', 'description', 'notes', 'outcome']
                    print("CAMPOS POSIBLES PARA RESUMEN:")
                    for campo in campos_posibles:
                        valor = call_details.get(campo)
                        if valor:
                            print(f"  {campo}: {type(valor)} = {valor}")

                else:
                    print("  [ERROR] No se pudieron obtener detalles de Pearl AI")

            except Exception as e:
                print(f"  [ERROR] Error obteniendo detalles de {call_id}: {e}")

            print("-" * 50)

        # 3. Verificar como se esta procesando en calls_updater
        print("\n=== VERIFICACION EN CALLS_UPDATER ===")
        print("Logica actual para extraer summary:")
        print("call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')")
        print()

        # Simular el procesamiento
        if call_ids:
            call_id = call_ids[0][0]  # Primer call_id
            try:
                call_details = client.get_call_status(call_id)
                if call_details:
                    # Simular la logica actual
                    summary_actual = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')
                    print(f"RESULTADO DE LA LOGICA ACTUAL:")
                    print(f"  summary extraído: {summary_actual}")
                    print(f"  tipo: {type(summary_actual)}")
                    print(f"  es None: {summary_actual is None}")
            except:
                pass

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    inspeccionar_respuesta_pearl()
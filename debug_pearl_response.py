#!/usr/bin/env python3
"""
Debug de las respuestas de Pearl AI para entender call_ids inválidos
"""

import mysql.connector
from dotenv import load_dotenv
import json

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

def debug_pearl_responses():
    conn = get_railway_connection()
    if not conn:
        return

    cursor = conn.cursor()

    print("DEBUG DE RESPUESTAS PEARL AI")
    print("=" * 60)

    # 1. Buscar leads que tienen pearl_call_response para ver la respuesta original
    cursor.execute("""
        SELECT l.id, l.nombre, l.telefono, l.call_status,
               l.pearl_call_response, l.call_id, l.updated_at
        FROM leads l
        WHERE l.pearl_call_response IS NOT NULL
        AND l.pearl_call_response != ''
        AND l.updated_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY l.updated_at DESC
        LIMIT 5
    """)

    responses = cursor.fetchall()

    for lead_id, nombre, telefono, call_status, pearl_response, call_id, updated in responses:
        print(f"\nLEAD {lead_id}: {nombre} ({telefono})")
        print(f"Call Status: {call_status}")
        print(f"Call ID: {call_id}")
        print(f"Actualizado: {updated}")

        if pearl_response:
            try:
                # Intentar parsear como JSON
                response_data = json.loads(pearl_response)
                print("Pearl Response (parsed):")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))

                # Analizar el call_id en la respuesta
                if 'id' in response_data:
                    response_call_id = response_data['id']
                    print(f"Call ID en respuesta: {response_call_id}")

                    # Verificar si este call_id existe en pearl_calls
                    cursor.execute("SELECT status, summary FROM pearl_calls WHERE call_id = %s", (response_call_id,))
                    pearl_record = cursor.fetchone()

                    if pearl_record:
                        status, summary = pearl_record
                        print(f"Estado en pearl_calls: {status}")
                        if summary:
                            print(f"Resumen: {summary[:100]}...")
                    else:
                        print("⚠️ Call ID NO encontrado en pearl_calls")

            except json.JSONDecodeError:
                print("Pearl Response (raw):")
                print(pearl_response[:500] + "..." if len(pearl_response) > 500 else pearl_response)

        print("-" * 60)

    # 2. Verificar call_ids recientes que fallan
    print("\n\n2. CALL_IDS RECIENTES QUE FALLAN:")
    cursor.execute("""
        SELECT call_id, created_at, updated_at, lead_id
        FROM pearl_calls
        WHERE status = 'invalid_call_id'
        AND created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        ORDER BY created_at DESC
        LIMIT 5
    """)

    recent_fails = cursor.fetchall()

    for call_id, created, updated, lead_id in recent_fails:
        print(f"\nCall ID: {call_id}")
        print(f"Lead ID: {lead_id}")
        print(f"Creado: {created}")
        print(f"Invalidado: {updated}")

        # Buscar la respuesta original en leads
        cursor.execute("""
            SELECT pearl_call_response FROM leads
            WHERE id = %s AND pearl_call_response IS NOT NULL
        """, (lead_id,))

        lead_response = cursor.fetchone()
        if lead_response and lead_response[0]:
            try:
                response_data = json.loads(lead_response[0])
                print("Respuesta Pearl original:")
                if 'id' in response_data:
                    print(f"  ID: {response_data['id']}")
                if 'success' in response_data:
                    print(f"  Success: {response_data['success']}")
                if 'message' in response_data:
                    print(f"  Message: {response_data['message']}")
            except:
                print(f"  Raw: {lead_response[0][:200]}...")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    debug_pearl_responses()
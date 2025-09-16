#!/usr/bin/env python3
"""
Recupera los summaries faltantes de Pearl AI usando los call_ids
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

def recuperar_summaries(limit=50):
    """Recupera summaries faltantes de Pearl AI"""

    print("=== RECUPERACION DE SUMMARIES ===")
    print(f"Fecha/hora: {datetime.now()}")
    print(f"Procesando hasta {limit} registros...")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Obtener registros sin summary pero con call_id
        cursor.execute("""
            SELECT id, call_id, lead_id, status, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            ORDER BY created_at DESC
            LIMIT %s
        """, [limit])

        registros = cursor.fetchall()

        if not registros:
            print("No hay registros que recuperar")
            return

        print(f"Encontrados {len(registros)} registros para recuperar summaries")
        print()

        # 2. Conectar a Pearl AI
        client = get_pearl_client()

        actualizados = 0
        errores = 0

        for id_registro, call_id, lead_id, status, created_at in registros:
            print(f"Procesando registro {id_registro} - Call ID: {call_id}")

            try:
                # Obtener detalles de Pearl AI
                call_details = client.get_call_status(call_id)

                if call_details:
                    # Extraer summary usando la misma lógica que calls_updater
                    summary = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')

                    if summary and summary.strip():
                        # Actualizar en la BD
                        cursor.execute("""
                            UPDATE pearl_calls
                            SET summary = %s, updated_at = NOW()
                            WHERE id = %s
                        """, [summary, id_registro])

                        conn.commit()
                        actualizados += 1
                        print(f"  [OK] Summary actualizado: {len(summary)} caracteres")

                        # Mostrar preview del summary
                        preview = summary[:100] + "..." if len(summary) > 100 else summary
                        print(f"  Preview: {preview}")

                    else:
                        print(f"  [SKIP] No hay summary en Pearl AI para este call_id")

                else:
                    print(f"  [ERROR] No se pudieron obtener detalles de Pearl AI")
                    errores += 1

            except Exception as e:
                print(f"  [ERROR] Error procesando {call_id}: {e}")
                errores += 1

            print()

        print("=" * 60)
        print("RESUMEN:")
        print(f"  Total procesados: {len(registros)}")
        print(f"  Summaries actualizados: {actualizados}")
        print(f"  Errores: {errores}")

        if actualizados > 0:
            print()
            print(f"[EXITO] Se recuperaron {actualizados} summaries!")

            # Verificar el estado final
            cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
            con_summary = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NULL OR summary = ''")
            sin_summary = cursor.fetchone()[0]

            print()
            print("ESTADO FINAL DE LA TABLA:")
            print(f"  CON summary: {con_summary}")
            print(f"  SIN summary: {sin_summary}")

        return actualizados

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cursor.close()
        conn.close()

def recuperar_summaries_masivo():
    """Recupera summaries en lotes para procesar todos"""

    print("=== RECUPERACION MASIVA DE SUMMARIES ===")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # Contar total sin summaries
        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
        """)
        total_sin_summary = cursor.fetchone()[0]

        print(f"Total de registros sin summary: {total_sin_summary}")

        if total_sin_summary == 0:
            print("No hay summaries para recuperar")
            return

        print(f"Procesando automáticamente los {total_sin_summary} registros...")

        # Procesar en lotes de 50
        lote_size = 50
        total_actualizados = 0

        for offset in range(0, total_sin_summary, lote_size):
            print(f"\n--- LOTE {offset//lote_size + 1} ---")
            print(f"Procesando registros {offset+1} a {min(offset+lote_size, total_sin_summary)}")

            actualizados = recuperar_summaries_con_offset(offset, lote_size)
            total_actualizados += actualizados

            if actualizados < lote_size:
                break

        print(f"\n[EXITO] RECUPERACION MASIVA COMPLETADA")
        print(f"Total summaries recuperados: {total_actualizados}")

    except Exception as e:
        print(f"ERROR en recuperacion masiva: {e}")
    finally:
        cursor.close()
        conn.close()

def recuperar_summaries_con_offset(offset, limit):
    """Version con offset para procesamiento masivo"""

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, call_id, lead_id, status, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, [limit, offset])

        registros = cursor.fetchall()

        if not registros:
            return 0

        client = get_pearl_client()
        actualizados = 0

        for id_registro, call_id, lead_id, status, created_at in registros:
            try:
                call_details = client.get_call_status(call_id)

                if call_details:
                    summary = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')

                    if summary and summary.strip():
                        cursor.execute("""
                            UPDATE pearl_calls
                            SET summary = %s, updated_at = NOW()
                            WHERE id = %s
                        """, [summary, id_registro])

                        conn.commit()
                        actualizados += 1
                        print(f"    [OK] Registro {id_registro}: {len(summary)} chars")

            except Exception as e:
                print(f"    [ERROR] {call_id}: {e}")

        return actualizados

    except Exception as e:
        print(f"ERROR en lote: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("OPCIONES:")
    print("1. Recuperar primeros 50 summaries")
    print("2. Recuperacion masiva (todos)")
    print()

    opcion = input("Selecciona opcion (1/2): ").strip()

    if opcion == "1":
        recuperar_summaries(50)
    elif opcion == "2":
        recuperar_summaries_masivo()
    else:
        print("Opcion invalida")
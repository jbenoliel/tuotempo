#!/usr/bin/env python3
"""
Recuperacion masiva optimizada de summaries de Railway
"""

import pymysql
from datetime import datetime
from pearl_caller import get_pearl_client
import time

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

def recuperar_todos_los_summaries():
    """Recupera TODOS los summaries faltantes de una vez"""

    print("=== RECUPERACION MASIVA DE SUMMARIES RAILWAY ===")
    print(f"Iniciado: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Verificar estado inicial
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        summaries_iniciales = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
        """)
        registros_recuperables = cursor.fetchone()[0]

        print("ESTADO INICIAL:")
        print(f"  Summaries existentes: {summaries_iniciales}")
        print(f"  Registros recuperables (status=4): {registros_recuperables}")
        print()

        if registros_recuperables == 0:
            print("No hay summaries para recuperar")
            return

        # 2. Obtener TODOS los registros recuperables
        print(f"Obteniendo {registros_recuperables} registros...")
        cursor.execute("""
            SELECT id, call_id, lead_id, created_at
            FROM pearl_calls
            WHERE call_id IS NOT NULL AND call_id != ''
            AND (summary IS NULL OR summary = '')
            AND status = '4'
            ORDER BY created_at DESC
        """)

        registros = cursor.fetchall()
        print(f"Registros obtenidos: {len(registros)}")
        print()

        # 3. Conectar a Pearl AI
        client = get_pearl_client()

        # 4. Procesar todos los registros
        actualizados = 0
        errores = 0
        sin_summary = 0

        start_time = time.time()

        print("PROCESANDO REGISTROS:")
        print("-" * 60)

        for i, (id_registro, call_id, lead_id, created_at) in enumerate(registros, 1):
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (len(registros) - i) / rate if rate > 0 else 0
                print(f"Progreso: {i}/{len(registros)} ({i/len(registros)*100:.1f}%) - {rate:.1f}/seg - ETA: {remaining/60:.1f}min")

            try:
                # Obtener detalles de Pearl AI
                call_details = client.get_call_status(call_id)

                if call_details:
                    # Extraer summary
                    summary = call_details.get('summary', {}).get('text') if isinstance(call_details.get('summary'), dict) else call_details.get('summary')

                    if summary and summary.strip():
                        # Actualizar en BD
                        cursor.execute("""
                            UPDATE pearl_calls
                            SET summary = %s, updated_at = NOW()
                            WHERE id = %s
                        """, [summary, id_registro])

                        actualizados += 1

                        if actualizados % 10 == 0:
                            conn.commit()  # Commit cada 10 actualizaciones

                    else:
                        sin_summary += 1

                else:
                    errores += 1

            except Exception as e:
                errores += 1
                if errores <= 5:  # Solo mostrar primeros 5 errores
                    print(f"  Error en {call_id}: {e}")

        # Commit final
        conn.commit()

        elapsed_time = time.time() - start_time

        print("-" * 60)
        print("RECUPERACION COMPLETADA")
        print(f"Tiempo total: {elapsed_time/60:.1f} minutos")
        print()

        print("RESULTADOS:")
        print(f"  Total procesados: {len(registros)}")
        print(f"  Summaries recuperados: {actualizados}")
        print(f"  Sin summary en Pearl: {sin_summary}")
        print(f"  Errores: {errores}")
        print()

        # 5. Verificar estado final
        cursor.execute("SELECT COUNT(*) FROM pearl_calls WHERE summary IS NOT NULL AND summary != ''")
        summaries_finales = cursor.fetchone()[0]

        print("ESTADO FINAL:")
        print(f"  Summaries antes: {summaries_iniciales}")
        print(f"  Summaries ahora: {summaries_finales}")
        print(f"  Summaries nuevos: {summaries_finales - summaries_iniciales}")

        if actualizados > 0:
            print()
            print(f"[EXITO] Se recuperaron {actualizados} summaries de Railway!")

        return actualizados

    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("RECUPERACION MASIVA DE SUMMARIES DE RAILWAY")
    print("=" * 60)
    print("Este proceso puede tardar varios minutos...")
    print()

    resultado = recuperar_todos_los_summaries()

    print()
    print("=" * 60)
    if resultado > 0:
        print(f"PROCESO COMPLETADO - {resultado} summaries recuperados")
    else:
        print("PROCESO COMPLETADO - No se recuperaron summaries")
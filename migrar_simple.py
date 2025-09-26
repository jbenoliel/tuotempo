#!/usr/bin/env python3
"""
Migración simple por pasos
"""

from config import settings
import pymysql

def get_connection():
    return pymysql.connect(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        port=settings.DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4'
    )

def migrar_simple():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            print("=== MIGRACION SIMPLE ===")

            # Estado inicial
            cursor.execute("SELECT COUNT(*) as total FROM leads WHERE call_status = 'no_selected'")
            inicial = cursor.fetchone()['total']
            print(f"Estado inicial: {inicial} leads con no_selected")

            # Paso 1: Migrar leads sin llamadas a NULL
            print("\n1. Migrando leads SIN llamadas a NULL...")
            cursor.execute("""
                UPDATE leads
                SET call_status = NULL, updated_at = NOW()
                WHERE call_status = 'no_selected'
                AND id NOT IN (
                    SELECT DISTINCT lead_id FROM pearl_calls WHERE lead_id IS NOT NULL
                )
            """)
            sin_llamadas = cursor.rowcount
            print(f"   Migrados a NULL: {sin_llamadas} leads")

            # Paso 2: Migrar a completed (con duración > 0 y summary)
            print("\n2. Migrando leads con llamadas completadas...")
            cursor.execute("""
                UPDATE leads l
                INNER JOIN (
                    SELECT pc.lead_id
                    FROM pearl_calls pc
                    INNER JOIN (
                        SELECT lead_id, MAX(call_time) as max_time
                        FROM pearl_calls GROUP BY lead_id
                    ) latest ON pc.lead_id = latest.lead_id AND pc.call_time = latest.max_time
                    WHERE pc.duration > 0
                    AND pc.summary IS NOT NULL
                    AND pc.summary != 'N/A'
                    AND pc.summary != ''
                ) completadas ON l.id = completadas.lead_id
                SET l.call_status = 'completed', l.updated_at = NOW()
                WHERE l.call_status = 'no_selected'
            """)
            completed = cursor.rowcount
            print(f"   Migrados a completed: {completed} leads")

            # Paso 3: Migrar a error (duration = 0 o call_id con invalid)
            print("\n3. Migrando leads con errores...")
            cursor.execute("""
                UPDATE leads l
                INNER JOIN (
                    SELECT pc.lead_id
                    FROM pearl_calls pc
                    INNER JOIN (
                        SELECT lead_id, MAX(call_time) as max_time
                        FROM pearl_calls GROUP BY lead_id
                    ) latest ON pc.lead_id = latest.lead_id AND pc.call_time = latest.max_time
                    WHERE pc.duration = 0
                    OR pc.call_id LIKE '%invalid%'
                    OR pc.call_id LIKE '%error%'
                ) errores ON l.id = errores.lead_id
                SET l.call_status = 'error', l.updated_at = NOW()
                WHERE l.call_status = 'no_selected'
            """)
            errores = cursor.rowcount
            print(f"   Migrados a error: {errores} leads")

            # Paso 4: El resto a no_answer
            print("\n4. Migrando resto a no_answer...")
            cursor.execute("""
                UPDATE leads l
                INNER JOIN (
                    SELECT DISTINCT lead_id FROM pearl_calls WHERE lead_id IS NOT NULL
                ) con_llamadas ON l.id = con_llamadas.lead_id
                SET l.call_status = 'no_answer', l.updated_at = NOW()
                WHERE l.call_status = 'no_selected'
            """)
            no_answer = cursor.rowcount
            print(f"   Migrados a no_answer: {no_answer} leads")

            # Verificación final
            print("\n=== RESULTADO FINAL ===")
            cursor.execute("SELECT COUNT(*) as total FROM leads WHERE call_status = 'no_selected'")
            final = cursor.fetchone()['total']
            print(f"Restantes con no_selected: {final}")

            cursor.execute("""
                SELECT
                    COALESCE(call_status, 'NULL') as status,
                    COUNT(*) as count
                FROM leads
                GROUP BY call_status
                ORDER BY count DESC
            """)
            distribucion = cursor.fetchall()

            print("Distribución final:")
            for d in distribucion:
                print(f"   {d['status']}: {d['count']} leads")

            print(f"\nTotal migrado: {sin_llamadas + completed + errores + no_answer}")

            # Confirmar
            conn.commit()
            print("\n✓ MIGRACION COMPLETADA")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrar_simple()
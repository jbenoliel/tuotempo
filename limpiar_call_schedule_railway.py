#!/usr/bin/env python3
"""
Script de limpieza para call_schedule en Railway
Elimina programaciones duplicadas y problemáticas
"""

import logging
from datetime import datetime
from reprogramar_llamadas_simple import get_pymysql_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def limpiar_call_schedule():
    """Limpia programaciones duplicadas y problemáticas"""

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la BD")
        return False

    print("=== LIMPIEZA DE CALL_SCHEDULE EN RAILWAY ===")
    print()

    try:
        with conn.cursor() as cursor:

            # 1. Contar registros antes de la limpieza
            cursor.execute("SELECT COUNT(*) as total FROM call_schedule")
            total_antes = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as cancelled FROM call_schedule WHERE status = 'cancelled'")
            cancelled_antes = cursor.fetchone()['cancelled']

            print(f"ESTADO INICIAL:")
            print(f"  Total registros: {total_antes}")
            print(f"  Registros cancelled: {cancelled_antes}")
            print()

            # 2. Cancelar programaciones de leads cerrados
            print("1. Cancelando programaciones de leads cerrados...")
            cursor.execute("""
                UPDATE call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                SET cs.status = 'cancelled',
                    cs.updated_at = NOW()
                WHERE l.lead_status = 'closed'
                AND cs.status = 'pending'
            """)
            leads_cerrados_actualizados = cursor.rowcount
            print(f"   Programaciones canceladas de leads cerrados: {leads_cerrados_actualizados}")

            # 3. Eliminar programaciones duplicadas canceladas (mantener solo la más reciente)
            print("2. Eliminando programaciones cancelled duplicadas...")
            cursor.execute("""
                DELETE cs1 FROM call_schedule cs1
                INNER JOIN call_schedule cs2
                WHERE cs1.id < cs2.id
                AND cs1.lead_id = cs2.lead_id
                AND cs1.status = 'cancelled'
                AND cs2.status = 'cancelled'
                AND DATE(cs1.created_at) = DATE(cs2.created_at)
            """)
            duplicadas_eliminadas = cursor.rowcount
            print(f"   Registros cancelled duplicados eliminados: {duplicadas_eliminadas}")

            # 4. Eliminar programaciones cancelled muy antiguas (más de 7 días)
            print("3. Eliminando programaciones cancelled antiguas...")
            cursor.execute("""
                DELETE FROM call_schedule
                WHERE status = 'cancelled'
                AND updated_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            antiguas_eliminadas = cursor.rowcount
            print(f"   Registros cancelled antiguos eliminados: {antiguas_eliminadas}")

            # 5. Limpiar programaciones huérfanas (sin lead correspondiente)
            print("4. Limpiando programaciones huérfanas...")
            cursor.execute("""
                DELETE cs FROM call_schedule cs
                LEFT JOIN leads l ON cs.lead_id = l.id
                WHERE l.id IS NULL
            """)
            huerfanas_eliminadas = cursor.rowcount
            print(f"   Programaciones huérfanas eliminadas: {huerfanas_eliminadas}")

            # 6. Verificar leads con demasiadas programaciones pendientes
            print("5. Verificando leads con múltiples programaciones pendientes...")
            cursor.execute("""
                SELECT lead_id, COUNT(*) as count
                FROM call_schedule
                WHERE status = 'pending'
                GROUP BY lead_id
                HAVING count > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            multiples_pendientes = cursor.fetchall()

            if multiples_pendientes:
                print("   Leads con múltiples programaciones pendientes:")
                for row in multiples_pendientes:
                    print(f"     Lead {row['lead_id']}: {row['count']} programaciones")

                # Mantener solo la programación más reciente para cada lead
                print("   Manteniendo solo la programación más reciente por lead...")
                cursor.execute("""
                    DELETE cs1 FROM call_schedule cs1
                    INNER JOIN (
                        SELECT lead_id, MAX(id) as max_id
                        FROM call_schedule
                        WHERE status = 'pending'
                        GROUP BY lead_id
                        HAVING COUNT(*) > 1
                    ) cs2 ON cs1.lead_id = cs2.lead_id
                    WHERE cs1.status = 'pending'
                    AND cs1.id != cs2.max_id
                """)
                pendientes_duplicadas = cursor.rowcount
                print(f"   Programaciones pendientes duplicadas eliminadas: {pendientes_duplicadas}")
            else:
                print("   No se encontraron leads con múltiples programaciones pendientes")
                pendientes_duplicadas = 0

            # Confirmar cambios
            conn.commit()

            # 7. Mostrar estado final
            cursor.execute("SELECT COUNT(*) as total FROM call_schedule")
            total_despues = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as cancelled FROM call_schedule WHERE status = 'cancelled'")
            cancelled_despues = cursor.fetchone()['cancelled']

            cursor.execute("SELECT COUNT(*) as pending FROM call_schedule WHERE status = 'pending'")
            pending_despues = cursor.fetchone()['pending']

            print()
            print("ESTADO FINAL:")
            print(f"  Total registros: {total_despues} (antes: {total_antes})")
            print(f"  Registros cancelled: {cancelled_despues} (antes: {cancelled_antes})")
            print(f"  Registros pending: {pending_despues}")
            print()
            print("RESUMEN DE LIMPIEZA:")
            print(f"  Registros eliminados total: {total_antes - total_despues}")
            print(f"  - Programaciones de leads cerrados: {leads_cerrados_actualizados}")
            print(f"  - Duplicadas cancelled: {duplicadas_eliminadas}")
            print(f"  - Antiguas cancelled: {antiguas_eliminadas}")
            print(f"  - Huérfanas: {huerfanas_eliminadas}")
            print(f"  - Pendientes duplicadas: {pendientes_duplicadas}")

            return True

    except Exception as e:
        logger.error(f"Error durante la limpieza: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verificar_leads_problematicos():
    """Verifica si los leads problemáticos siguen teniendo issues"""

    # Leads que reportaban warnings
    problematic_leads = [
        556, 558, 561, 562, 564, 563, 551, 566, 568, 565,
        570, 572, 567, 549, 571, 574, 575, 573, 569,
        2052, 2085, 2340, 2467
    ]

    conn = get_pymysql_connection()
    if not conn:
        return

    print()
    print("=== VERIFICACION POST-LIMPIEZA ===")

    try:
        with conn.cursor() as cursor:
            leads_str = ','.join(map(str, problematic_leads))

            cursor.execute(f"""
                SELECT cs.lead_id,
                       COUNT(*) as total_schedules,
                       SUM(CASE WHEN cs.status = 'pending' THEN 1 ELSE 0 END) as pending,
                       SUM(CASE WHEN cs.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                       l.lead_status
                FROM call_schedule cs
                LEFT JOIN leads l ON cs.lead_id = l.id
                WHERE cs.lead_id IN ({leads_str})
                GROUP BY cs.lead_id, l.lead_status
                ORDER BY total_schedules DESC
            """)

            results = cursor.fetchall()
            print(f"Estado de los {len(problematic_leads)} leads problemáticos:")

            for result in results:
                lead_id = result['lead_id']
                total = result['total_schedules']
                pending = result['pending']
                cancelled = result['cancelled']
                lead_status = result['lead_status'] or 'NO_EXISTE'

                print(f"  Lead {lead_id} ({lead_status}): {total} registros ({pending} pending, {cancelled} cancelled)")

        print()
        print("Los warnings deberían reducirse significativamente después de esta limpieza.")

    except Exception as e:
        logger.error(f"Error en verificación: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("LIMPIEZA DE CALL_SCHEDULE PARA RAILWAY")
    print("=" * 60)

    if limpiar_call_schedule():
        verificar_leads_problematicos()
        print()
        print("=" * 60)
        print("[EXITO] Limpieza completada exitosamente")
        print("Ejecuta este script en Railway para aplicar los cambios")
    else:
        print()
        print("[ERROR] La limpieza falló")
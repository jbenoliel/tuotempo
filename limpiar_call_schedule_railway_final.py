#!/usr/bin/env python3
"""
Script de limpieza final para call_schedule en Railway
Usa la misma configuracion que reporte_detallado_railway.py
"""

import pymysql
from datetime import datetime

# Configuracion de Railway (misma que reporte_detallado_railway.py)
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    """Crear conexion a Railway"""
    return pymysql.connect(**RAILWAY_CONFIG)

def limpiar_call_schedule_railway():
    """Ejecuta la limpieza en Railway directamente"""

    print("=== LIMPIEZA DE CALL_SCHEDULE EN RAILWAY ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Estado inicial
        print("1. VERIFICANDO ESTADO INICIAL...")
        cursor.execute("SELECT COUNT(*) as total FROM call_schedule")
        total_antes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) as cancelled FROM call_schedule WHERE status = 'cancelled'")
        cancelled_antes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) as pending FROM call_schedule WHERE status = 'pending'")
        pending_antes = cursor.fetchone()[0]

        print(f"   Total registros: {total_antes}")
        print(f"   Cancelled: {cancelled_antes}")
        print(f"   Pending: {pending_antes}")
        print()

        # 2. Cancelar programaciones de leads cerrados
        print("2. CANCELANDO PROGRAMACIONES DE LEADS CERRADOS...")
        cursor.execute("""
            UPDATE call_schedule cs
            JOIN leads l ON cs.lead_id = l.id
            SET cs.status = 'cancelled',
                cs.updated_at = NOW()
            WHERE l.lead_status = 'closed'
            AND cs.status = 'pending'
        """)
        leads_cerrados = cursor.rowcount
        print(f"   Programaciones canceladas: {leads_cerrados}")

        # 3. Eliminar duplicadas cancelled del mismo dia
        print("3. ELIMINANDO DUPLICADAS CANCELLED DEL MISMO DIA...")
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
        print(f"   Registros duplicados eliminados: {duplicadas_eliminadas}")

        # 4. Eliminar cancelled antiguos
        print("4. ELIMINANDO CANCELLED ANTIGUOS (>7 dias)...")
        cursor.execute("""
            DELETE FROM call_schedule
            WHERE status = 'cancelled'
            AND updated_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        antiguos_eliminados = cursor.rowcount
        print(f"   Registros antiguos eliminados: {antiguos_eliminados}")

        # 5. Eliminar huerfanas
        print("5. ELIMINANDO PROGRAMACIONES HUERFANAS...")
        cursor.execute("""
            DELETE cs FROM call_schedule cs
            LEFT JOIN leads l ON cs.lead_id = l.id
            WHERE l.id IS NULL
        """)
        huerfanas_eliminadas = cursor.rowcount
        print(f"   Programaciones huerfanas eliminadas: {huerfanas_eliminadas}")

        # 6. Verificar leads con multiples pending
        print("6. VERIFICANDO LEADS CON MULTIPLES PENDING...")
        cursor.execute("""
            SELECT lead_id, COUNT(*) as count
            FROM call_schedule
            WHERE status = 'pending'
            GROUP BY lead_id
            HAVING count > 1
            ORDER BY count DESC
            LIMIT 5
        """)
        multiples = cursor.fetchall()

        if multiples:
            print("   Leads con multiples programaciones pending:")
            for lead_id, count in multiples:
                print(f"     Lead {lead_id}: {count} programaciones")

            # Eliminar pending duplicadas (mantener la mas reciente)
            print("   Eliminando pending duplicadas...")
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
            pending_duplicadas = cursor.rowcount
            print(f"   Pending duplicadas eliminadas: {pending_duplicadas}")
        else:
            print("   No se encontraron leads con multiples pending")
            pending_duplicadas = 0

        # Confirmar cambios
        conn.commit()

        # 7. Estado final
        print()
        print("7. ESTADO FINAL...")
        cursor.execute("SELECT COUNT(*) as total FROM call_schedule")
        total_despues = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) as cancelled FROM call_schedule WHERE status = 'cancelled'")
        cancelled_despues = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) as pending FROM call_schedule WHERE status = 'pending'")
        pending_despues = cursor.fetchone()[0]

        print(f"   Total registros: {total_despues} (antes: {total_antes})")
        print(f"   Cancelled: {cancelled_despues} (antes: {cancelled_antes})")
        print(f"   Pending: {pending_despues} (antes: {pending_antes})")
        print()

        # 8. Verificar leads problematicos
        print("8. VERIFICANDO LEADS PROBLEMATICOS...")
        leads_problematicos = [556, 558, 561, 562, 564, 563, 551, 566, 568, 565, 570, 572, 567, 549, 571, 574, 575, 573, 569, 2052, 2085, 2340, 2467]
        leads_str = ','.join(map(str, leads_problematicos))

        cursor.execute(f"""
            SELECT cs.lead_id,
                   COUNT(*) as total,
                   SUM(CASE WHEN cs.status = 'pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN cs.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                   l.lead_status
            FROM call_schedule cs
            LEFT JOIN leads l ON cs.lead_id = l.id
            WHERE cs.lead_id IN ({leads_str})
            GROUP BY cs.lead_id, l.lead_status
            ORDER BY total DESC
        """)

        results = cursor.fetchall()
        if results:
            print("   Estado actual de leads problematicos:")
            for lead_id, total, pending, cancelled, lead_status in results:
                status = lead_status or 'NO_EXISTE'
                print(f"     Lead {lead_id} ({status}): {total} total ({pending} pending, {cancelled} cancelled)")
        else:
            print("   No se encontraron registros para leads problematicos")

        print()
        print("=" * 60)
        print("RESUMEN DE LIMPIEZA:")
        print(f"  Registros eliminados total: {total_antes - total_despues}")
        print(f"  - Leads cerrados cancelados: {leads_cerrados}")
        print(f"  - Duplicadas cancelled: {duplicadas_eliminadas}")
        print(f"  - Antiguos cancelled: {antiguos_eliminados}")
        print(f"  - Huerfanas: {huerfanas_eliminadas}")
        print(f"  - Pending duplicadas: {pending_duplicadas}")
        print()
        print("[EXITO] LIMPIEZA COMPLETADA EN RAILWAY")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    limpiar_call_schedule_railway()
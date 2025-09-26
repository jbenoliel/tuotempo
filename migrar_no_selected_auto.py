#!/usr/bin/env python3
"""
Script para migrar leads con no_selected según su historial real (AUTO)
"""

import os
import sys
from config import settings
import pymysql
import logging

# Configurar logging simple
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_pymysql_connection():
    """Obtiene conexión PyMySQL con configuración de Railway"""
    try:
        return pymysql.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            port=settings.DB_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
    except Exception as e:
        logger.error(f"Error conectando a la BD: {e}")
        return None

def migrar_no_selected_auto():
    """
    Migra leads con no_selected según su historial real de llamadas (automático)
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False

    try:
        with conn.cursor() as cursor:
            print("=== MIGRACION DE LEADS CON no_selected ===")

            # 1. Verificar estado inicial
            cursor.execute("SELECT COUNT(*) as total FROM leads WHERE call_status = 'no_selected'")
            total_inicial = cursor.fetchone()['total']
            print(f"Leads con no_selected al inicio: {total_inicial}")

            # 2. PASO 1: Migrar leads SIN llamadas a NULL
            print("\n--- PASO 1: Leads sin llamadas => NULL ---")

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads l
                WHERE l.call_status = 'no_selected'
                AND NOT EXISTS (
                    SELECT 1 FROM pearl_calls pc WHERE pc.lead_id = l.id
                )
            """)
            sin_llamadas_count = cursor.fetchone()['count']
            print(f"Leads sin llamadas que se migraran a NULL: {sin_llamadas_count}")

            if sin_llamadas_count > 0:
                cursor.execute("""
                    UPDATE leads l
                    SET call_status = NULL,
                        updated_at = NOW()
                    WHERE l.call_status = 'no_selected'
                    AND NOT EXISTS (
                        SELECT 1 FROM pearl_calls pc WHERE pc.lead_id = l.id
                    )
                """)
                migrados_null = cursor.rowcount
                print(f"Migrados a NULL: {migrados_null} leads")
            else:
                migrados_null = 0

            # 3. PASO 2: Migrar leads CON llamadas al estado de su última llamada
            print("\n--- PASO 2: Leads con llamadas => Estado ultima llamada ---")

            cursor.execute("""
                SELECT
                    l.id,
                    l.nombre,
                    CASE
                        WHEN pc.duration > 0 AND (pc.summary IS NOT NULL AND pc.summary != 'N/A' AND pc.summary != '')
                        THEN 'completed'
                        WHEN pc.duration = 0 OR pc.call_id LIKE '%invalid%' OR pc.call_id LIKE '%error%'
                        THEN 'error'
                        ELSE 'no_answer'
                    END as nuevo_estado
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                INNER JOIN (
                    SELECT lead_id, MAX(call_time) as max_time
                    FROM pearl_calls
                    GROUP BY lead_id
                ) latest ON pc.lead_id = latest.lead_id AND pc.call_time = latest.max_time
                WHERE l.call_status = 'no_selected'
                ORDER BY l.id
            """)
            con_llamadas = cursor.fetchall()

            print(f"Leads con llamadas que se migraran: {len(con_llamadas)}")

            # Agrupar por nuevo estado
            estados_count = {}
            for lead in con_llamadas:
                estado = lead['nuevo_estado']
                estados_count[estado] = estados_count.get(estado, 0) + 1

            print("Distribucion de nuevos estados:")
            for estado, count in sorted(estados_count.items()):
                print(f"  {estado}: {count} leads")

            # Ejecutar migraciones por estado
            migrados_total = 0
            for estado in ['completed', 'error', 'no_answer']:
                if estado in estados_count:
                    try:
                        print(f"Migrando leads a estado: {estado}")
                        cursor.execute("""
                            UPDATE leads l
                            INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                            INNER JOIN (
                                SELECT lead_id, MAX(call_time) as max_time
                                FROM pearl_calls
                                GROUP BY lead_id
                            ) latest ON pc.lead_id = latest.lead_id AND pc.call_time = latest.max_time
                            SET l.call_status = %s,
                                l.updated_at = NOW()
                            WHERE l.call_status = 'no_selected'
                            AND CASE
                                WHEN pc.duration > 0 AND (pc.summary IS NOT NULL AND pc.summary != 'N/A' AND pc.summary != '')
                                THEN 'completed'
                                WHEN pc.duration = 0 OR pc.call_id LIKE '%invalid%' OR pc.call_id LIKE '%error%'
                                THEN 'error'
                                ELSE 'no_answer'
                            END = %s
                        """, (estado, estado))

                        migrados_estado = cursor.rowcount
                        migrados_total += migrados_estado
                        print(f"Migrados a {estado}: {migrados_estado} leads")
                    except Exception as ex:
                        print(f"Error migrando estado {estado}: {ex}")
                        raise ex

            # 4. Verificar resultado final
            print("\n--- VERIFICACION FINAL ---")
            cursor.execute("SELECT COUNT(*) as total FROM leads WHERE call_status = 'no_selected'")
            total_final = cursor.fetchone()['total']
            print(f"Leads con no_selected al final: {total_final}")

            cursor.execute("""
                SELECT call_status, COUNT(*) as count
                FROM leads
                WHERE call_status IS NULL OR call_status IN ('completed', 'error', 'no_answer', 'busy', 'calling')
                GROUP BY call_status
                ORDER BY count DESC
            """)
            estados_finales = cursor.fetchall()

            print("Distribucion final de call_status:")
            for estado in estados_finales:
                status_name = estado['call_status'] if estado['call_status'] else 'NULL'
                print(f"  {status_name}: {estado['count']} leads")

            print(f"\n=== RESUMEN DE MIGRACION ===")
            print(f"Total inicial con no_selected: {total_inicial}")
            print(f"Migrados a NULL (sin llamadas): {migrados_null}")
            print(f"Migrados por historial (con llamadas): {migrados_total}")
            print(f"Total procesado: {migrados_null + migrados_total}")
            print(f"Restantes con no_selected: {total_final}")

            # Confirmar automáticamente
            conn.commit()
            print("\n✓ Migracion completada automaticamente")
            return True

    except Exception as e:
        print(f"Error durante migracion: {e}")
        logger.error("Error durante migracion: %s", str(e))
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Iniciando migracion automatica de no_selected...")

    print("EJECUTANDO: Migracion automatica de leads con 'no_selected'")
    print("  - Sin llamadas => NULL")
    print("  - Con llamadas => Estado de la ultima llamada")
    print()

    success = migrar_no_selected_auto()

    if success:
        logger.info("Migracion completada exitosamente")
    else:
        logger.error("Migracion fallo")
        sys.exit(1)
#!/usr/bin/env python3
"""
Script para migrar leads con no_selected según su historial real:
- Sin llamadas → NULL
- Con llamadas → Estado de la última llamada
"""

import os
import sys
from config import settings
import pymysql
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

def migrar_no_selected():
    """
    Migra leads con no_selected según su historial real de llamadas
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False

    try:
        with conn.cursor() as cursor:
            print("=== MIGRACIÓN DE LEADS CON no_selected ===\n")

            # 1. Verificar estado inicial
            cursor.execute("SELECT COUNT(*) as total FROM leads WHERE call_status = 'no_selected'")
            total_inicial = cursor.fetchone()['total']
            print(f"Leads con no_selected al inicio: {total_inicial}")

            # 2. PASO 1: Migrar leads SIN llamadas a NULL
            print("\n--- PASO 1: Leads sin llamadas → NULL ---")

            # Primero contar
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads l
                WHERE l.call_status = 'no_selected'
                AND NOT EXISTS (
                    SELECT 1 FROM pearl_calls pc WHERE pc.lead_id = l.id
                )
            """)
            sin_llamadas_count = cursor.fetchone()['count']
            print(f"Leads sin llamadas que se migrarán a NULL: {sin_llamadas_count}")

            # Ejecutar migración
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
            print("\n--- PASO 2: Leads con llamadas → Estado última llamada ---")

            # Obtener leads que necesitan migración con su estado correcto
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

            print(f"Leads con llamadas que se migrarán: {len(con_llamadas)}")

            # Agrupar por nuevo estado para mostrar estadísticas
            estados_count = {}
            for lead in con_llamadas:
                estado = lead['nuevo_estado']
                estados_count[estado] = estados_count.get(estado, 0) + 1

            print("Distribución de nuevos estados:")
            for estado, count in sorted(estados_count.items()):
                print(f"  {estado}: {count} leads")

            # Ejecutar migraciones por estado
            migrados_total = 0
            for estado in ['completed', 'error', 'no_answer']:
                if estado in estados_count:
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

            # 4. Verificar resultado final
            print("\n--- VERIFICACIÓN FINAL ---")
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

            print("Distribución final de call_status:")
            for estado in estados_finales:
                status_name = estado['call_status'] if estado['call_status'] else 'NULL'
                print(f"  {status_name}: {estado['count']} leads")

            print(f"\n=== RESUMEN DE MIGRACIÓN ===")
            print(f"Total inicial con no_selected: {total_inicial}")
            print(f"Migrados a NULL (sin llamadas): {migrados_null}")
            print(f"Migrados por historial (con llamadas): {migrados_total}")
            print(f"Total procesado: {migrados_null + migrados_total}")
            print(f"Restantes con no_selected: {total_final}")

            # Confirmar cambios
            print(f"\nConfirmar migracion? (SI/no): ", end="")
            if input().strip() == "SI":
                conn.commit()
                print("Migracion completada y confirmada")
                return True
            else:
                conn.rollback()
                print("Migracion cancelada - cambios revertidos")
                return False

    except Exception as e:
        logger.error(f"Error durante migración: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Iniciando migración lógica de no_selected...")

    print("ATENCION: Este script migrara leads con 'no_selected' segun su historial real:")
    print("  - Sin llamadas => NULL")
    print("  - Con llamadas => Estado de la ultima llamada")
    print()

    success = migrar_no_selected()

    if success:
        logger.info("Migración completada exitosamente")
    else:
        logger.error("Migración falló")
        sys.exit(1)
#!/usr/bin/env python3
"""
Script para analizar leads con no_selected vs su historial real de llamadas
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

def analizar_no_selected():
    """
    Analiza leads con no_selected vs su historial real de llamadas
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False

    try:
        with conn.cursor() as cursor:
            print("=== ANÁLISIS DE LEADS CON no_selected ===\n")

            # 1. Total leads con no_selected
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM leads
                WHERE call_status = 'no_selected'
            """)
            total_no_selected = cursor.fetchone()['total']
            print(f"Total leads con call_status = 'no_selected': {total_no_selected}")

            # 2. Leads con no_selected que SÍ tienen llamadas en pearl_calls (query simplificada)
            cursor.execute("""
                SELECT
                    l.id,
                    l.nombre,
                    l.apellidos,
                    l.telefono,
                    l.call_status,
                    l.call_attempts_count,
                    l.last_call_attempt,
                    COUNT(pc.id) as pearl_calls_count,
                    MAX(pc.call_time) as ultima_llamada
                FROM leads l
                LEFT JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.call_status = 'no_selected'
                GROUP BY l.id, l.nombre, l.apellidos, l.telefono, l.call_status, l.call_attempts_count, l.last_call_attempt
                HAVING COUNT(pc.id) > 0
                ORDER BY pearl_calls_count DESC, ultima_llamada DESC
                LIMIT 10
            """)
            con_llamadas = cursor.fetchall()

            print(f"\nLeads con 'no_selected' que SÍ tienen llamadas registradas:")
            print(f"Total: {len(con_llamadas)} (mostrando primeros 10)")

            for lead in con_llamadas:
                print(f"\n  Lead {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                print(f"    Tel: {lead['telefono']}")
                print(f"    Llamadas en Pearl: {lead['pearl_calls_count']}")
                print(f"    call_attempts_count: {lead['call_attempts_count']}")
                print(f"    Última llamada: {lead['ultima_llamada']}")
                print(f"    last_call_attempt: {lead['last_call_attempt']}")

            # 3. Count total de leads con no_selected que tienen llamadas
            cursor.execute("""
                SELECT COUNT(DISTINCT l.id) as count
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.call_status = 'no_selected'
            """)
            total_con_llamadas = cursor.fetchone()['count']

            # 4. Leads con no_selected que NO tienen llamadas
            sin_llamadas = total_no_selected - total_con_llamadas

            print(f"\n=== RESUMEN ===")
            print(f"Leads con 'no_selected' que SÍ han tenido llamadas: {total_con_llamadas}")
            print(f"Leads con 'no_selected' que NO han tenido llamadas: {sin_llamadas}")

            # 5. Analizar qué estados deberían tener los que sí han tenido llamadas
            cursor.execute("""
                SELECT
                    CASE
                        WHEN pc.duration > 0 AND (pc.summary IS NOT NULL AND pc.summary != 'N/A')
                        THEN 'completed'
                        WHEN pc.duration = 0 OR pc.call_id LIKE '%invalid%'
                        THEN 'error'
                        ELSE 'no_answer'
                    END as estado_sugerido,
                    COUNT(*) as count
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                INNER JOIN (
                    SELECT lead_id, MAX(call_time) as max_time
                    FROM pearl_calls
                    GROUP BY lead_id
                ) latest ON pc.lead_id = latest.lead_id AND pc.call_time = latest.max_time
                WHERE l.call_status = 'no_selected'
                GROUP BY estado_sugerido
                ORDER BY count DESC
            """)
            estados_sugeridos = cursor.fetchall()

            print(f"\n=== ESTADOS SUGERIDOS PARA LEADS CON LLAMADAS ===")
            for estado in estados_sugeridos:
                print(f"  {estado['estado_sugerido']}: {estado['count']} leads")

            # 6. Ejemplos específicos para verificar la lógica
            cursor.execute("""
                SELECT
                    l.id,
                    l.nombre,
                    l.telefono,
                    pc.call_time,
                    pc.duration,
                    pc.summary,
                    pc.call_id,
                    CASE
                        WHEN pc.duration > 0 AND (pc.summary IS NOT NULL AND pc.summary != 'N/A')
                        THEN 'completed'
                        WHEN pc.duration = 0 OR pc.call_id LIKE '%invalid%'
                        THEN 'error'
                        ELSE 'no_answer'
                    END as estado_sugerido
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                INNER JOIN (
                    SELECT lead_id, MAX(call_time) as max_time
                    FROM pearl_calls
                    GROUP BY lead_id
                ) latest ON pc.lead_id = latest.lead_id AND pc.call_time = latest.max_time
                WHERE l.call_status = 'no_selected'
                ORDER BY pc.call_time DESC
                LIMIT 5
            """)
            ejemplos = cursor.fetchall()

            print(f"\n=== EJEMPLOS DE CORRECCIONES NECESARIAS ===")
            for ej in ejemplos:
                print(f"\n  Lead {ej['id']}: {ej['nombre']}")
                print(f"    Actual: no_selected → Debería ser: {ej['estado_sugerido']}")
                print(f"    Última llamada: {ej['call_time']}")
                print(f"    Duración: {ej['duration']}s")
                print(f"    Call ID: {ej['call_id']}")
                if ej['summary'] and ej['summary'] != 'N/A':
                    summary_preview = ej['summary'][:60] + "..." if len(ej['summary']) > 60 else ej['summary']
                    print(f"    Summary: {summary_preview}")

            return True

    except Exception as e:
        logger.error(f"Error analizando no_selected: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Analizando leads con no_selected vs historial real...")
    success = analizar_no_selected()

    if success:
        logger.info("Análisis completado")
    else:
        logger.error("Error durante el análisis")
        sys.exit(1)
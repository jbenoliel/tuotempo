#!/usr/bin/env python3
"""
Script para verificar el estado del lead 2336 que estaba causando el error
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

def verificar_lead_2336():
    """
    Verifica el estado específico del lead 2336
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False

    try:
        with conn.cursor() as cursor:
            # 1. Buscar el lead 2336
            cursor.execute("""
                SELECT id, nombre, apellidos, telefono, telefono2,
                       call_status, selected_for_calling, call_attempts_count,
                       last_call_attempt, call_error_message,
                       lead_status, closure_reason,
                       status_level_1, status_level_2, resultado_llamada
                FROM leads
                WHERE id = 2336
            """)
            lead = cursor.fetchone()

            print("=== ESTADO DEL LEAD 2336 ===")
            if lead:
                print(f"ID: {lead['id']}")
                print(f"Nombre: {lead['nombre']} {lead['apellidos']}")
                print(f"Teléfono: {lead['telefono']}")
                print(f"Teléfono2: {lead['telefono2']}")
                print(f"Call Status: {lead['call_status']}")
                print(f"Selected for Calling: {lead['selected_for_calling']}")
                print(f"Call Attempts: {lead['call_attempts_count']}")
                print(f"Last Call Attempt: {lead['last_call_attempt']}")
                print(f"Call Error Message: {lead['call_error_message']}")
                print(f"Lead Status: {lead['lead_status']}")
                print(f"Closure Reason: {lead['closure_reason']}")
                print(f"Status Level 1: {lead['status_level_1']}")
                print(f"Status Level 2: {lead['status_level_2']}")
                print(f"Resultado Llamada: {lead['resultado_llamada']}")
            else:
                print("¡LEAD 2336 NO ENCONTRADO!")
                return False

            # 2. Buscar llamadas programadas para este lead
            cursor.execute("""
                SELECT id, lead_id, scheduled_at, attempt_number, status, last_outcome,
                       created_at, updated_at
                FROM call_schedule
                WHERE lead_id = 2336
                ORDER BY created_at DESC
                LIMIT 5
            """)
            scheduled_calls = cursor.fetchall()

            print(f"\n=== LLAMADAS PROGRAMADAS (últimas 5) ===")
            if scheduled_calls:
                for call in scheduled_calls:
                    print(f"  - ID: {call['id']}, Scheduled: {call['scheduled_at']}")
                    print(f"    Attempt: {call['attempt_number']}, Status: {call['status']}")
                    print(f"    Outcome: {call['last_outcome']}")
                    print(f"    Created: {call['created_at']}, Updated: {call['updated_at']}")
                    print()
            else:
                print("  No hay llamadas programadas para este lead")

            # 3. Buscar llamadas de Pearl AI para este lead
            cursor.execute("""
                SELECT call_id, phone_number, call_time, duration, summary,
                       collected_info, recording_url, lead_id
                FROM pearl_calls
                WHERE lead_id = 2336
                ORDER BY call_time DESC
                LIMIT 3
            """)
            pearl_calls = cursor.fetchall()

            print(f"\n=== LLAMADAS DE PEARL AI (últimas 3) ===")
            if pearl_calls:
                for call in pearl_calls:
                    print(f"  - Call ID: {call['call_id']}")
                    print(f"    Phone: {call['phone_number']}, Duration: {call['duration']}")
                    print(f"    Time: {call['call_time']}")
                    print(f"    Summary: {call['summary'][:100] if call['summary'] else 'N/A'}...")
                    print()
            else:
                print("  No hay llamadas de Pearl AI registradas para este lead")

            return True

    except Exception as e:
        logger.error(f"Error verificando lead 2336: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Verificando estado del lead 2336...")
    success = verificar_lead_2336()

    if success:
        logger.info("Verificación completada")
    else:
        logger.error("Error durante la verificación")
        sys.exit(1)
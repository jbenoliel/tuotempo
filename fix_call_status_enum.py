#!/usr/bin/env python3
"""
Script para actualizar el ENUM call_status y corregir los estados incorrectos.
1. Actualizar leads con 'no_selected' y 'selected' a NULL
2. Modificar el ENUM para eliminar estos valores
"""

import os
import sys
from config import DATABASE_CONFIG
import pymysql
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_pymysql_connection():
    """Obtiene conexión PyMySQL con configuración de Railway"""
    try:
        return pymysql.connect(
            host=DATABASE_CONFIG['host'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            database=DATABASE_CONFIG['database'],
            port=DATABASE_CONFIG['port'],
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
    except Exception as e:
        logger.error(f"Error conectando a la BD: {e}")
        return None

def fix_call_status_enum():
    """
    Actualiza el ENUM call_status eliminando no_selected y selected
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False

    try:
        with conn.cursor() as cursor:
            # 1. Contar leads con estados problemáticos
            cursor.execute("""
                SELECT
                    call_status,
                    COUNT(*) as count
                FROM leads
                WHERE call_status IN ('no_selected', 'selected')
                GROUP BY call_status
            """)
            problematic_states = cursor.fetchall()

            if problematic_states:
                logger.info("Estados problemáticos encontrados:")
                for state in problematic_states:
                    logger.info(f"  - {state['call_status']}: {state['count']} leads")

                # 2. Actualizar leads con estados problemáticos a NULL
                logger.info("Actualizando estados problemáticos a NULL...")
                cursor.execute("""
                    UPDATE leads
                    SET call_status = NULL,
                        updated_at = NOW()
                    WHERE call_status IN ('no_selected', 'selected')
                """)
                updated_count = cursor.rowcount
                logger.info(f"Actualizados {updated_count} leads a call_status = NULL")
            else:
                logger.info("No se encontraron estados problemáticos")

            # 3. Modificar el ENUM para eliminar estados problemáticos
            logger.info("Modificando ENUM call_status...")
            cursor.execute("""
                ALTER TABLE leads
                MODIFY COLUMN call_status ENUM('calling', 'completed', 'error', 'busy', 'no_answer')
                DEFAULT NULL
                COMMENT 'Estado actual de la llamada automática'
            """)
            logger.info("ENUM modificado exitosamente")

            # 4. Verificar el resultado
            cursor.execute("""
                SELECT
                    call_status,
                    COUNT(*) as count
                FROM leads
                GROUP BY call_status
                ORDER BY call_status
            """)
            final_states = cursor.fetchall()

            logger.info("Estados finales:")
            for state in final_states:
                status_name = state['call_status'] if state['call_status'] else 'NULL'
                logger.info(f"  - {status_name}: {state['count']} leads")

            conn.commit()
            logger.info("Proceso completado exitosamente")
            return True

    except Exception as e:
        logger.error(f"Error durante el proceso: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Iniciando corrección del ENUM call_status...")

    # Confirmación
    print("\n¿Estás seguro de que quieres ejecutar este script?")
    print("Esto modificará el ENUM call_status y actualizará los leads con estados 'no_selected' y 'selected' a NULL")
    confirmation = input("Escribe 'SI' para continuar: ")

    if confirmation != 'SI':
        print("Operación cancelada")
        sys.exit(0)

    success = fix_call_status_enum()

    if success:
        logger.info("Script completado exitosamente")
    else:
        logger.error("Script falló")
        sys.exit(1)
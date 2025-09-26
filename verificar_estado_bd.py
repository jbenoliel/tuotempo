#!/usr/bin/env python3
"""
Script para verificar el estado actual de call_status en la base de datos
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

def verificar_estado_bd():
    """
    Verifica el estado actual de la tabla leads y call_status
    """
    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False

    try:
        with conn.cursor() as cursor:
            # 1. Verificar estructura actual de call_status
            cursor.execute("""
                SELECT COLUMN_TYPE, COLUMN_DEFAULT, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'leads'
                AND COLUMN_NAME = 'call_status'
                AND TABLE_SCHEMA = DATABASE()
            """)
            column_info = cursor.fetchone()

            print("=== ESTRUCTURA ACTUAL DE call_status ===")
            if column_info:
                print(f"Tipo: {column_info['COLUMN_TYPE']}")
                print(f"Valor por defecto: {column_info['COLUMN_DEFAULT']}")
                print(f"Permite NULL: {column_info['IS_NULLABLE']}")
            else:
                print("¡COLUMNA call_status NO ENCONTRADA!")
                return False

            # 2. Contar estados actuales
            cursor.execute("""
                SELECT
                    call_status,
                    COUNT(*) as count
                FROM leads
                GROUP BY call_status
                ORDER BY count DESC
            """)
            estados = cursor.fetchall()

            print("\n=== DISTRIBUCIÓN DE ESTADOS ===")
            total_leads = 0
            for estado in estados:
                status_name = estado['call_status'] if estado['call_status'] else 'NULL'
                count = estado['count']
                total_leads += count
                print(f"  {status_name}: {count} leads")

            print(f"TOTAL: {total_leads} leads")

            # 3. Verificar si hay estados problemáticos
            cursor.execute("""
                SELECT COUNT(*) as problematic_count
                FROM leads
                WHERE call_status IN ('no_selected', 'selected')
            """)
            problematic = cursor.fetchone()

            print(f"\n=== ESTADOS PROBLEMÁTICOS ===")
            print(f"Leads con 'no_selected' o 'selected': {problematic['problematic_count']}")

            # 4. Ejemplos de leads con estados problemáticos
            if problematic['problematic_count'] > 0:
                cursor.execute("""
                    SELECT id, nombre, apellidos, telefono, call_status, selected_for_calling
                    FROM leads
                    WHERE call_status IN ('no_selected', 'selected')
                    LIMIT 5
                """)
                ejemplos = cursor.fetchall()

                print("\nEjemplos:")
                for ejemplo in ejemplos:
                    print(f"  - Lead {ejemplo['id']}: {ejemplo['nombre']} {ejemplo['apellidos']}")
                    print(f"    Tel: {ejemplo['telefono']}, Status: {ejemplo['call_status']}, Selected: {ejemplo['selected_for_calling']}")

            # 5. Verificar leads que están seleccionados para llamar
            cursor.execute("""
                SELECT call_status, COUNT(*) as count
                FROM leads
                WHERE selected_for_calling = TRUE
                GROUP BY call_status
                ORDER BY count DESC
            """)
            seleccionados = cursor.fetchall()

            print(f"\n=== LEADS SELECCIONADOS PARA LLAMAR ===")
            if seleccionados:
                for sel in seleccionados:
                    status_name = sel['call_status'] if sel['call_status'] else 'NULL'
                    print(f"  {status_name}: {sel['count']} leads")
            else:
                print("  No hay leads seleccionados para llamar")

            return True

    except Exception as e:
        logger.error(f"Error verificando estado BD: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Verificando estado actual de la base de datos...")
    success = verificar_estado_bd()

    if success:
        logger.info("Verificación completada")
    else:
        logger.error("Error durante la verificación")
        sys.exit(1)
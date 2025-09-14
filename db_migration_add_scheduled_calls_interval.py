"""
Migración para añadir configuración de intervalo del daemon de llamadas programadas.
Fecha: 2025-09-XX
Descripción: Inserta la configuración 'scheduled_calls_interval_minutes' en scheduler_config.
"""

import logging
from mysql.connector import Error
from db import get_connection

# Configurar logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración para agregar el intervalo de ejecución del daemon."""
    conn = get_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos para migración de intervalo.")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scheduler_config (config_key, config_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                config_value = VALUES(config_value),
                description  = VALUES(description),
                updated_at   = CURRENT_TIMESTAMP
            """,
            (
                'scheduled_calls_interval_minutes',
                '5',
                'Intervalo en minutos para ejecutar el daemon de llamadas programadas'
            )
        )
        conn.commit()
        logger.info("Configuración 'scheduled_calls_interval_minutes' insertada/actualizada.")
        return True
    except Error as e:
        logger.error(f"Error insertando configuración de intervalo: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def rollback_migration():
    """Elimina la configuración de intervalo del daemon."""
    conn = get_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos para rollback de intervalo.")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM scheduler_config WHERE config_key = %s",
            ('scheduled_calls_interval_minutes',)
        )
        conn.commit()
        logger.info("Configuración 'scheduled_calls_interval_minutes' eliminada.")
        return True
    except Error as e:
        logger.error(f"Error eliminando configuración de intervalo: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
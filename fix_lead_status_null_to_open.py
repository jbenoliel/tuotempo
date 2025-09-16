#!/usr/bin/env python3
"""
Script para normalizar el estado de los leads:
- Convierte todos los registros con lead_status = NULL a 'open'
- Proporciona reporte antes/después y modo dry-run por defecto

Uso:
  python fix_lead_status_null_to_open.py            # Dry-run (no escribe)
  python fix_lead_status_null_to_open.py --apply    # Aplica cambios (commit)

Requisitos:
- Configuración de conexión a BD a través de reprogramar_llamadas_simple.get_pymysql_connection
"""
import argparse
import logging
from reprogramar_llamadas_simple import get_pymysql_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def contar_por_estado(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS c FROM leads WHERE lead_status IS NULL")
        nulls = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM leads WHERE lead_status = 'open'")
        abiertos = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM leads WHERE lead_status = 'closed'")
        cerrados = cursor.fetchone()["c"]
    return nulls, abiertos, cerrados


def main():
    parser = argparse.ArgumentParser(description="Normaliza lead_status NULL a 'open'")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios (por defecto es dry-run)"
    )
    args = parser.parse_args()

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return 1

    try:
        nulls, abiertos, cerrados = contar_por_estado(conn)
        logger.info(f"Estado actual: NULL={nulls}, open={abiertos}, closed={cerrados}")

        with conn.cursor() as cursor:
            # Previsualizar cuántos se actualizarían
            cursor.execute("SELECT COUNT(*) AS c FROM leads WHERE lead_status IS NULL")
            a_actualizar = cursor.fetchone()["c"]
            logger.info(f"Leads a actualizar (NULL -> 'open'): {a_actualizar}")

            if a_actualizar == 0:
                logger.info("No hay nada que actualizar. Saliendo.")
                return 0

            if args.apply:
                cursor.execute(
                    """
                    UPDATE leads
                    SET lead_status = 'open',
                        updated_at = NOW()
                    WHERE lead_status IS NULL
                    """
                )
                conn.commit()
                logger.info(f"Actualización realizada. Filas afectadas: {cursor.rowcount}")
            else:
                logger.info("Dry-run: no se han realizado cambios. Use --apply para aplicar.")

        nulls2, abiertos2, cerrados2 = contar_por_estado(conn)
        logger.info(f"Estado final: NULL={nulls2}, open={abiertos2}, closed={cerrados2}")
        return 0

    except Exception as e:
        logger.error(f"Error durante la normalización: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

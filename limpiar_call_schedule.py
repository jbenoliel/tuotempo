#!/usr/bin/env python3
"""
Limpieza segura de la tabla call_schedule en Railway.

Características:
- Dry-run por defecto (no escribe cambios)
- Filtros opcionales por lead_id y status
- Límite por antigüedad con --days (ej. borrar "cancelled" más antiguos que N días)
- Limpieza de huérfanos (registros sin lead correspondiente)

Ejemplos:
  # Ver (dry-run) cuántos registros "cancelled" de hace > 30 días serían eliminados
  python limpiar_call_schedule.py --status cancelled --days 30

  # Aplicar la limpieza anterior
  python limpiar_call_schedule.py --status cancelled --days 30 --apply

  # Ver (dry-run) solo para un lead concreto (ej. 2467) con > 7 días
  python limpiar_call_schedule.py --lead-id 2467 --status cancelled --days 7

  # Eliminar huérfanos (sin lead correspondiente)
  python limpiar_call_schedule.py --orphans-only
  python limpiar_call_schedule.py --orphans-only --apply
"""
import argparse
import logging
from typing import Optional
from reprogramar_llamadas_simple import get_pymysql_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def contar(conn, lead_id: Optional[int], status: Optional[str], days: Optional[int]) -> int:
    where = []
    params = []

    if lead_id is not None:
        where.append("lead_id = %s")
        params.append(lead_id)
    if status is not None:
        where.append("status = %s")
        params.append(status)
    if days is not None and days > 0:
        where.append("scheduled_at < NOW() - INTERVAL %s DAY")
        params.append(int(days))

    sql = "SELECT COUNT(*) AS c FROM call_schedule"
    if where:
        sql += " WHERE " + " AND ".join(where)

    with conn.cursor() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchone()["c"]


def borrar(conn, lead_id: Optional[int], status: Optional[str], days: Optional[int]) -> int:
    where = []
    params = []

    if lead_id is not None:
        where.append("lead_id = %s")
        params.append(lead_id)
    if status is not None:
        where.append("status = %s")
        params.append(status)
    if days is not None and days > 0:
        where.append("scheduled_at < NOW() - INTERVAL %s DAY")
        params.append(int(days))

    sql = "DELETE FROM call_schedule"
    if where:
        sql += " WHERE " + " AND ".join(where)

    with conn.cursor() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.rowcount


def contar_huerfanos(conn) -> int:
    sql = (
        "SELECT COUNT(*) AS c "
        "FROM call_schedule cs "
        "LEFT JOIN leads l ON l.id = cs.lead_id "
        "WHERE l.id IS NULL"
    )
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()["c"]


def borrar_huerfanos(conn) -> int:
    sql = (
        "DELETE cs FROM call_schedule cs "
        "LEFT JOIN leads l ON l.id = cs.lead_id "
        "WHERE l.id IS NULL"
    )
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.rowcount


def main():
    parser = argparse.ArgumentParser(description="Limpia call_schedule con filtros y dry-run por defecto")
    parser.add_argument("--lead-id", type=int, default=None, help="Filtrar por lead_id específico")
    parser.add_argument("--status", type=str, default=None, help="Filtrar por status (p.ej., cancelled, pending)")
    parser.add_argument("--days", type=int, default=None, help="Eliminar solo registros con scheduled_at más antiguos que N días")
    parser.add_argument("--orphans-only", action="store_true", help="Limpiar únicamente registros huérfanos")
    parser.add_argument("--apply", action="store_true", help="Aplicar cambios (por defecto solo dry-run)")

    args = parser.parse_args()

    conn = get_pymysql_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return 1

    try:
        if args.orphans_only:
            total = contar_huerfanos(conn)
            logger.info(f"Huérfanos en call_schedule: {total}")
            if total == 0:
                logger.info("No hay huérfanos que eliminar. Saliendo.")
                return 0
            if args.apply:
                borrados = borrar_huerfanos(conn)
                conn.commit()
                logger.info(f"Huérfanos eliminados: {borrados}")
            else:
                logger.info("Dry-run: no se eliminaron huérfanos. Use --apply para aplicar.")
            return 0

        # Limpieza normal con filtros
        total = contar(conn, args.lead_id, args.status, args.days)
        logger.info(
            "Candidatos a eliminar en call_schedule: %s (filtros: lead_id=%s, status=%s, days>%s)",
            total, args.lead_id, args.status, args.days
        )

        if total == 0:
            logger.info("No hay registros que cumplan las condiciones. Saliendo.")
            return 0

        if args.apply:
            borrados = borrar(conn, args.lead_id, args.status, args.days)
            conn.commit()
            logger.info(f"Registros eliminados: {borrados}")
        else:
            logger.info("Dry-run: no se eliminaron registros. Use --apply para aplicar.")

        return 0

    except Exception as e:
        logger.error(f"Error durante la limpieza: {e}")
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

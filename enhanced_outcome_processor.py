#!/usr/bin/env python3
"""
Procesador mejorado de outcomes para manejar correctamente el Outcome 6 (Failed)
según las reglas de negocio:
- 1 vez Outcome 6 = Problema temporal centralita → "Volver a llamar"
- 2+ veces Outcome 6 = Número erróneo → "Numero erroneo"
"""

import pymysql
import logging
from datetime import datetime
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def determine_lead_status_from_outcomes(lead_id: int, max_attempts: int = 6) -> dict:
    """
    Determina el status correcto de un lead basado en sus outcomes de Pearl calls

    Args:
        lead_id: ID del lead
        max_attempts: Máximo número de intentos permitidos

    Returns:
        dict: {
            'status_level_1': str,
            'status_level_2': str,
            'reason': str,
            'should_close': bool
        }
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Obtener información del lead y sus outcomes
            cursor.execute("""
                SELECT
                    l.id,
                    l.nombre,
                    l.apellidos,
                    l.call_attempts_count,
                    l.status_level_1,
                    l.status_level_2,
                    GROUP_CONCAT(pc.outcome ORDER BY pc.call_time ASC) as outcomes_sequence
                FROM leads l
                LEFT JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.id = %s
                GROUP BY l.id
            """, (lead_id,))

            lead_data = cursor.fetchone()
            if not lead_data:
                return {
                    'status_level_1': None,
                    'status_level_2': None,
                    'reason': 'Lead no encontrado',
                    'should_close': False
                }

            # Analizar outcomes
            outcomes_str = lead_data['outcomes_sequence']
            if not outcomes_str:
                return {
                    'status_level_1': 'Volver a llamar',
                    'status_level_2': 'Sin llamadas registradas',
                    'reason': 'No hay outcomes registrados',
                    'should_close': False
                }

            # Convertir outcomes a lista de enteros
            outcomes = []
            for outcome_str in outcomes_str.split(','):
                if outcome_str and outcome_str != 'None':
                    try:
                        outcomes.append(int(outcome_str))
                    except ValueError:
                        continue

            # Contar tipos de outcomes
            outcome_6_count = outcomes.count(6)  # Failed
            outcome_4_count = outcomes.count(4)  # Ocupado
            outcome_5_count = outcomes.count(5)  # Colgó
            outcome_7_count = outcomes.count(7)  # No contesta

            # Aplicar reglas de negocio

            # REGLA 1: 2+ Outcomes 6 = Número erróneo
            if outcome_6_count >= 2:
                return {
                    'status_level_1': 'Numero erroneo',
                    'status_level_2': 'Fallo multiple veces',
                    'reason': f'Outcome 6 (Failed) repetido {outcome_6_count} veces',
                    'should_close': True
                }

            # REGLA 2: 1 Outcome 6 = Problema temporal centralita
            elif outcome_6_count == 1:
                return {
                    'status_level_1': 'Volver a llamar',
                    'status_level_2': 'Fallo centralita',
                    'reason': '1 outcome 6 (Failed) - problema temporal centralita',
                    'should_close': False
                }

            # REGLA 3: Solo outcomes de no-contacto (4, 5, 7)
            elif all(o in [4, 5, 7] for o in outcomes):
                call_attempts = lead_data['call_attempts_count'] or len(outcomes)

                if call_attempts >= max_attempts:
                    return {
                        'status_level_1': 'No Interesado',
                        'status_level_2': 'Maximo intentos',
                        'reason': f'Máximo intentos alcanzado ({call_attempts}/{max_attempts}) - solo no-contacto',
                        'should_close': True
                    }
                else:
                    # Determinar subtipo según outcome más frecuente
                    if outcome_4_count > outcome_5_count and outcome_4_count > outcome_7_count:
                        status_level_2 = 'no disponible cliente'
                    elif outcome_5_count > outcome_7_count:
                        status_level_2 = 'cortado'
                    elif outcome_7_count > 0:
                        status_level_2 = 'buzon'
                    else:
                        status_level_2 = 'no disponible cliente'

                    return {
                        'status_level_1': 'Volver a llamar',
                        'status_level_2': status_level_2,
                        'reason': 'Solo outcomes de no-contacto',
                        'should_close': False
                    }

            # REGLA 4: Outcomes desconocidos o mixtos
            else:
                return {
                    'status_level_1': 'Volver a llamar',
                    'status_level_2': 'Revisar manualmente',
                    'reason': f'Outcomes mixtos o desconocidos: {set(outcomes)}',
                    'should_close': False
                }

    except Exception as e:
        logger.error(f"Error determinando status para lead {lead_id}: {e}")
        return {
            'status_level_1': None,
            'status_level_2': None,
            'reason': f'Error: {e}',
            'should_close': False
        }
    finally:
        conn.close()

def process_lead_outcomes(lead_id: int, auto_update: bool = False) -> bool:
    """
    Procesa los outcomes de un lead y opcionalmente actualiza su status

    Args:
        lead_id: ID del lead a procesar
        auto_update: Si True, actualiza automáticamente el status en BD

    Returns:
        bool: True si el procesamiento fue exitoso
    """

    # Determinar nuevo status
    status_info = determine_lead_status_from_outcomes(lead_id)

    if not status_info['status_level_1']:
        logger.error(f"No se pudo determinar status para lead {lead_id}: {status_info['reason']}")
        return False

    logger.info(f"Lead {lead_id}: {status_info['status_level_1']} - {status_info['reason']}")

    if auto_update:
        return update_lead_status(lead_id, status_info)

    return True

def update_lead_status(lead_id: int, status_info: dict) -> bool:
    """
    Actualiza el status de un lead en la base de datos
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Actualizar status del lead
            update_sql = """
                UPDATE leads
                SET
                    status_level_1 = %s,
                    status_level_2 = %s,
                    updated_at = NOW()
                WHERE id = %s
            """

            cursor.execute(update_sql, (
                status_info['status_level_1'],
                status_info['status_level_2'],
                lead_id
            ))

            # Si debe cerrarse, actualizar lead_status
            if status_info['should_close']:
                cursor.execute("""
                    UPDATE leads
                    SET lead_status = 'closed'
                    WHERE id = %s
                """, (lead_id,))

            conn.commit()

            logger.info(f"Lead {lead_id} actualizado: {status_info['status_level_1']} - {status_info['status_level_2']}")
            return True

    except Exception as e:
        logger.error(f"Error actualizando lead {lead_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        conn.close()

def process_all_pending_outcomes(limit: int = 100) -> dict:
    """
    Procesa todos los leads que necesitan actualización de status basado en outcomes

    Args:
        limit: Número máximo de leads a procesar

    Returns:
        dict: Estadísticas del procesamiento
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Buscar leads que pueden necesitar actualización
            # (leads con pearl_calls pero sin status definido o con status problemático)
            cursor.execute("""
                SELECT DISTINCT l.id
                FROM leads l
                INNER JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE (
                    l.status_level_1 IS NULL
                    OR l.status_level_1 = 'None'
                    OR l.status_level_1 = ''
                    OR (l.status_level_1 = 'Volver a llamar' AND l.call_attempts_count >= 6)
                )
                AND l.lead_status != 'closed'
                LIMIT %s
            """, (limit,))

            leads_to_process = cursor.fetchall()

        stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'numero_erroneo': 0,
            'volver_a_llamar': 0,
            'no_interesado': 0
        }

        for lead in leads_to_process:
            lead_id = lead['id']

            try:
                # Procesar lead
                status_info = determine_lead_status_from_outcomes(lead_id)

                if status_info['status_level_1']:
                    # Actualizar en BD
                    if update_lead_status(lead_id, status_info):
                        stats['updated'] += 1

                        # Contar por categoría
                        if status_info['status_level_1'] == 'Numero erroneo':
                            stats['numero_erroneo'] += 1
                        elif status_info['status_level_1'] == 'Volver a llamar':
                            stats['volver_a_llamar'] += 1
                        elif status_info['status_level_1'] == 'No Interesado':
                            stats['no_interesado'] += 1
                    else:
                        stats['errors'] += 1
                else:
                    stats['errors'] += 1

                stats['processed'] += 1

            except Exception as e:
                logger.error(f"Error procesando lead {lead_id}: {e}")
                stats['errors'] += 1
                stats['processed'] += 1

        logger.info(f"Procesamiento completado: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error en procesamiento masivo: {e}")
        return {'error': str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    # Ejemplo de uso
    print("=== PROCESADOR MEJORADO DE OUTCOMES ===")

    # Procesar todos los leads pendientes
    stats = process_all_pending_outcomes(limit=50)

    if 'error' in stats:
        print(f"Error: {stats['error']}")
    else:
        print(f"Resultados:")
        print(f"  Procesados: {stats['processed']}")
        print(f"  Actualizados: {stats['updated']}")
        print(f"  Errores: {stats['errors']}")
        print(f"  Numero erroneo: {stats['numero_erroneo']}")
        print(f"  Volver a llamar: {stats['volver_a_llamar']}")
        print(f"  No Interesado: {stats['no_interesado']}")
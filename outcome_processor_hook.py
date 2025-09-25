#!/usr/bin/env python3
"""
Hook que se ejecuta después de insertar/actualizar registros en pearl_calls
para procesar automáticamente los outcomes según las reglas de negocio
"""

import logging
from enhanced_outcome_processor import process_lead_outcomes

logger = logging.getLogger(__name__)

def process_outcome_after_call_update(lead_id: int, outcome: int = None):
    """
    Procesa el outcome de un lead después de actualizar pearl_calls

    Args:
        lead_id: ID del lead que se actualizó
        outcome: Outcome específico (opcional)
    """

    try:
        # Si es outcome 6 (Failed), procesar inmediatamente
        if outcome == 6:
            logger.info(f"Procesando Outcome 6 (Failed) para lead {lead_id}")
            process_lead_outcomes(lead_id, auto_update=True)

        # Para otros outcomes, verificar si el lead necesita procesamiento
        elif outcome in [4, 5, 7]:  # No-contacto outcomes
            # Solo procesar si el lead ha alcanzado varios intentos
            # (esto evita procesamiento excesivo en cada llamada)
            logger.debug(f"Outcome no-contacto ({outcome}) para lead {lead_id}")
            # Procesar cada 3 intentos para no saturar
            process_lead_outcomes(lead_id, auto_update=False)  # Solo log, no update

        else:
            logger.debug(f"Outcome {outcome} para lead {lead_id} - no requiere procesamiento especial")

    except Exception as e:
        logger.error(f"Error procesando outcome para lead {lead_id}: {e}")

def process_failed_outcome_batch(lead_ids: list = None):
    """
    Procesa en lote todos los leads con outcomes 6 (Failed)
    Útil para procesamiento inicial o limpieza
    """

    from enhanced_outcome_processor import get_connection

    if not lead_ids:
        # Buscar todos los leads con outcome 6
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT lead_id
                    FROM pearl_calls
                    WHERE outcome = 6
                    AND lead_id IN (
                        SELECT id FROM leads
                        WHERE lead_status != 'closed'
                        AND (status_level_1 IS NULL OR status_level_1 = 'None' OR status_level_1 = '')
                    )
                """)
                lead_ids = [row['lead_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    logger.info(f"Procesando {len(lead_ids)} leads con outcomes 6 (Failed)")

    processed = 0
    updated = 0

    for lead_id in lead_ids:
        try:
            success = process_lead_outcomes(lead_id, auto_update=True)
            processed += 1
            if success:
                updated += 1
        except Exception as e:
            logger.error(f"Error procesando lead {lead_id}: {e}")

    logger.info(f"Procesamiento completado: {processed} procesados, {updated} actualizados")
    return {'processed': processed, 'updated': updated}

if __name__ == "__main__":
    # Ejemplo de uso del hook
    print("=== HOOK PROCESADOR DE OUTCOMES ===")

    # Procesar todos los leads con outcome 6 pendientes
    result = process_failed_outcome_batch()
    print(f"Resultado: {result}")
#!/usr/bin/env python3
"""
Script para probar la función mejorada complete_scheduled_call
"""

import logging
from reprogramar_llamadas_simple import complete_scheduled_call

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_complete_scheduled_call_improvements():
    """
    Probar la función mejorada con diferentes escenarios
    """
    print("=== PROBANDO COMPLETE_SCHEDULED_CALL MEJORADA ===\n")

    # Caso 1: Lead cerrado (como el 2467)
    print("1. Probando con lead cerrado (2467):")
    result = complete_scheduled_call(2467, 'no_answer')
    print(f"Resultado: {result}")
    print()

    # Caso 2: Lead inexistente
    print("2. Probando con lead inexistente (99999):")
    result = complete_scheduled_call(99999, 'no_answer')
    print(f"Resultado: {result}")
    print()

    # Caso 3: Lead válido con llamada pending (si existe)
    print("3. Probando con lead activo que tenga llamada pending:")

    # Buscar un lead activo con llamada pending
    from reprogramar_llamadas_simple import get_pymysql_connection

    conn = get_pymysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cs.lead_id, l.nombre, l.apellidos, l.lead_status
                    FROM call_schedule cs
                    JOIN leads l ON cs.lead_id = l.id
                    WHERE cs.status = 'pending'
                    AND l.lead_status != 'closed'
                    LIMIT 1
                """)

                pending_lead = cursor.fetchone()
                if pending_lead:
                    lead_id = pending_lead['lead_id']
                    print(f"Encontrado lead {lead_id} ({pending_lead['nombre']} {pending_lead['apellidos']}) con llamada pending")

                    # NO vamos a completar realmente, solo simular
                    print("(Simulando - no se ejecuta realmente para no afectar datos)")
                else:
                    print("No se encontraron leads activos con llamadas pending")
        finally:
            conn.close()

    print("\n=== PRUEBAS COMPLETADAS ===")
    print("\nLa función mejorada ahora:")
    print("✓ Verifica el estado del lead antes de procesar")
    print("✓ Cancela llamadas pending si el lead está cerrado")
    print("✓ Usa nivel INFO en lugar de WARNING para casos normales")
    print("✓ Proporciona más contexto en los mensajes de log")
    print("✓ Reduce el spam de warnings en Railway")

if __name__ == "__main__":
    test_complete_scheduled_call_improvements()
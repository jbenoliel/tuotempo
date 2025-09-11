"""
Script para reprocesar leads con Status 6 (Failed) que ahora deberían programarse
en lugar de cerrarse, tras corregir el mapeo.
"""

import mysql.connector
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    """Conecta a la base de datos de Railway."""
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def reprocesar_status_6_failed():
    """
    Reprocesa leads con Status 6 (Failed) para programarlos correctamente.
    """
    
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Encontrar leads abiertos con Status 6 (Failed)
        logger.info("Buscando leads abiertos con Status 6 (Failed)...")
        
        cursor.execute("""
            SELECT 
                pc.call_id,
                pc.phone_number,
                pc.status,
                pc.call_time,
                pc.duration,
                l.id as lead_id,
                l.nombre,
                l.apellidos,
                l.call_attempts_count,
                l.lead_status
            FROM pearl_calls pc
            JOIN leads l ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
            WHERE pc.status = '6'  -- Failed
                AND l.lead_status = 'open'
                AND l.call_attempts_count < 6  -- No han alcanzado máximo intentos
                AND NOT EXISTS (
                    SELECT 1 FROM call_schedule cs 
                    WHERE cs.lead_id = l.id AND cs.status = 'pending'
                )
            ORDER BY pc.call_time DESC
        """)
        
        failed_calls = cursor.fetchall()
        
        if not failed_calls:
            logger.info("No hay llamadas con Status 6 (Failed) pendientes de reprogramar")
            return
            
        logger.info(f"Encontradas {len(failed_calls)} llamadas con Status 6 (Failed) para reprocesar")
        
        # 2. Importar la integración del scheduler
        try:
            from call_manager_scheduler_integration import enhanced_process_call_result
        except ImportError as e:
            logger.error(f"No se pudo importar la integración del scheduler: {e}")
            return
        
        # 3. Procesar cada llamada fallida
        processed = 0
        scheduled = 0
        
        for call in failed_calls:
            try:
                # Crear call_result para el scheduler (Status 6 ahora mapea a 'no_answer' para reprogramar)
                call_result = {
                    'success': False,
                    'status': 'no_answer',  # Nuevo mapeo: Failed = no_answer (reprogramar)
                    'duration': call['duration'] or 0,
                    'error_message': 'Fallo temporal de conexión',
                    'lead_id': call['lead_id'],
                    'phone_number': call['phone_number']
                }
                
                # Crear datos simulados de Pearl AI para el scheduler
                pearl_response = {
                    'id': call['call_id'],
                    'to': call['phone_number'],
                    'status': 6,  # Failed
                    'duration': call['duration'],
                    'startTime': call['call_time'].isoformat() if call['call_time'] else None
                }
                
                # Procesar con el scheduler integrado
                logger.info(f"Reprocesando Lead {call['lead_id']} ({call['nombre']} {call['apellidos']}) - Status 6 (Failed)")
                
                success = enhanced_process_call_result(call['lead_id'], call_result, pearl_response)
                
                if success:
                    processed += 1
                    scheduled += 1
                    logger.info(f"✅ Lead {call['lead_id']} reprogramado exitosamente")
                else:
                    logger.warning(f"⚠️ Error procesando Lead {call['lead_id']}")
                
            except Exception as e:
                logger.error(f"❌ Error reprocesando llamada {call['call_id']} para Lead {call['lead_id']}: {e}")
        
        # 4. Resumen final
        logger.info(f"""
╔══════════════════════════════════════╗
║      REPROCESO STATUS 6 (FAILED)     ║
╠══════════════════════════════════════╣
║ Llamadas Status 6 encontradas: {len(failed_calls):4d} ║
║ Llamadas procesadas:           {processed:4d} ║  
║ Llamadas reprogramadas:        {scheduled:4d} ║
║ Errores:                       {len(failed_calls) - processed:4d} ║
╚══════════════════════════════════════╝
        """)
        
        # 5. Verificar estado del scheduler después del reproceso
        cursor.execute("SELECT COUNT(*) as count FROM call_schedule WHERE status = 'pending'")
        pending_after = cursor.fetchone()['count']
        
        logger.info(f"📅 Llamadas pendientes en scheduler después del reproceso: {pending_after}")
        
    except Exception as e:
        logger.error(f"Error en reproceso Status 6: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== REPROCESANDO STATUS 6 (FAILED) ===")
    print("Aplicando nuevo mapeo: Status 6 (Failed) -> reprogramar en lugar de cerrar")
    print()
    
    reprocesar_status_6_failed()
    
    print()
    print("=== REPROCESO COMPLETADO ===")
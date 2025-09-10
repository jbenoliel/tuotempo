"""
Script para reprocesar llamadas fallidas de hoy que no fueron registradas en el scheduler.
Esto corrige el problema identificado donde las funciones de mapeo no funcionaban correctamente.
"""

import mysql.connector
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

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

def reprocesar_llamadas_fallidas():
    """
    Reprocesa todas las llamadas fallidas de hoy que no están en el scheduler.
    
    Pearl AI Status:
    - 4: Completed (Exitosa - no reprogramar)
    - 5: Busy (Ocupado - REPROGRAMAR)
    - 6: Failed (Fallo - REPROGRAMAR)
    - 7: NoAnswer (No contesta - REPROGRAMAR)
    """
    
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Encontrar llamadas fallidas de hoy que deberían estar en scheduler
        logger.info("Buscando llamadas fallidas de hoy sin programar...")
        
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
            WHERE DATE(pc.call_time) = CURDATE()
                AND pc.status IN ('5', '6', '7')  -- Busy, Failed, NoAnswer
                AND l.lead_status = 'open'
                AND NOT EXISTS (
                    SELECT 1 FROM call_schedule cs 
                    WHERE cs.lead_id = l.id AND cs.status = 'pending'
                )
            ORDER BY pc.call_time DESC
        """)
        
        failed_calls = cursor.fetchall()
        
        if not failed_calls:
            logger.info("No hay llamadas fallidas pendientes de reprogramar")
            return
            
        logger.info(f"Encontradas {len(failed_calls)} llamadas fallidas para reprocesar")
        
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
                # Mapear status de Pearl AI
                status_mapping = {
                    '5': 'busy',      # Busy - REPROGRAMAR
                    '6': 'error',     # Failed - REPROGRAMAR  
                    '7': 'no_answer'  # NoAnswer - REPROGRAMAR
                }
                
                error_mapping = {
                    '5': 'Línea ocupada',
                    '6': 'Llamada fallida',
                    '7': 'No contesta'
                }
                
                outcome = status_mapping.get(call['status'])
                error_message = error_mapping.get(call['status'])
                
                # Crear call_result para el scheduler
                call_result = {
                    'success': False,
                    'status': outcome,
                    'duration': call['duration'] or 0,
                    'error_message': error_message,
                    'lead_id': call['lead_id'],
                    'phone_number': call['phone_number']
                }
                
                # Crear datos simulados de Pearl AI para el scheduler
                pearl_response = {
                    'id': call['call_id'],
                    'to': call['phone_number'],
                    'status': int(call['status']),
                    'duration': call['duration'],
                    'startTime': call['call_time'].isoformat() if call['call_time'] else None
                }
                
                # Procesar con el scheduler integrado
                logger.info(f"Reprocesando Lead {call['lead_id']} ({call['nombre']} {call['apellidos']}) - Status {call['status']} ({outcome})")
                
                success = enhanced_process_call_result(call['lead_id'], call_result, pearl_response)
                
                if success:
                    processed += 1
                    if outcome in ['busy', 'error', 'no_answer']:
                        scheduled += 1
                        logger.info(f"✅ Lead {call['lead_id']} reprogramado exitosamente")
                    else:
                        logger.info(f"✅ Lead {call['lead_id']} procesado (cerrado)")
                else:
                    logger.warning(f"⚠️ Error procesando Lead {call['lead_id']}")
                
            except Exception as e:
                logger.error(f"❌ Error reprocesando llamada {call['call_id']} para Lead {call['lead_id']}: {e}")
        
        # 4. Resumen final
        logger.info(f"""
╔══════════════════════════════════════╗
║           RESUMEN REPROCESO          ║
╠══════════════════════════════════════╣
║ Llamadas fallidas encontradas: {len(failed_calls):4d} ║
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
        logger.error(f"Error en reproceso: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== REPROCESANDO LLAMADAS FALLIDAS DE HOY ===")
    print("Corrigiendo problema de mapeo de status de Pearl AI")
    print()
    
    reprocesar_llamadas_fallidas()
    
    print()
    print("=== REPROCESO COMPLETADO ===")
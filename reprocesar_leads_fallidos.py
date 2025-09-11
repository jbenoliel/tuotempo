"""
Script para reprocesar leads que fallaron por errores de call_status truncation
"""

import mysql.connector
from datetime import datetime, timedelta
import logging
import json

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

# Lista de IDs de leads que aparecían en los errores
FAILED_LEAD_IDS = [
    2019, 2025, 2457, 612, 2404, 2423, 503, 2427, 2033, 2424, 
    608, 2436, 2041, 614, 2415, 618, 615, 617, 610, 626, 630
]

def reprocesar_leads_fallidos():
    """
    Busca las llamadas más recientes de los leads que fallaron y las reprocesa.
    """
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar las llamadas más recientes para estos leads
        logger.info(f"Buscando llamadas recientes para {len(FAILED_LEAD_IDS)} leads fallidos...")
        
        # Crear la consulta con los IDs de leads
        lead_ids_str = ','.join(map(str, FAILED_LEAD_IDS))
        
        # Primero ver qué columnas existen
        cursor.execute("DESCRIBE pearl_calls")
        columns = cursor.fetchall()
        logger.info("Columnas en pearl_calls:")
        for col in columns:
            logger.info(f"  {col['Field']}: {col['Type']}")
        
        cursor.execute(f"""
            SELECT 
                pc.call_id,
                pc.phone_number,
                pc.status,
                pc.call_time,
                pc.duration,
                pc.summary,
                pc.recording_url,
                l.id as lead_id,
                l.nombre,
                l.apellidos,
                l.call_status as current_call_status,
                l.call_attempts_count,
                l.last_call_attempt
            FROM pearl_calls pc
            JOIN leads l ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
            WHERE l.id IN ({lead_ids_str})
                AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY l.id, pc.call_time DESC
        """)
        
        recent_calls = cursor.fetchall()
        
        if not recent_calls:
            logger.info("No se encontraron llamadas recientes para reprocesar")
            return
            
        logger.info(f"📞 Encontradas {len(recent_calls)} llamadas recientes para reprocesar")
        
        # Importar las funciones necesarias
        try:
            from call_manager_scheduler_integration import enhanced_process_call_result
        except ImportError as e:
            logger.error(f"No se pudo importar enhanced_process_call_result: {e}")
            return
            
        # Agrupar por lead_id para procesar solo la más reciente de cada lead
        leads_processed = set()
        processed_count = 0
        success_count = 0
        
        for call in recent_calls:
            lead_id = call['lead_id']
            
            # Solo procesar una vez por lead (la más reciente)
            if lead_id in leads_processed:
                continue
                
            leads_processed.add(lead_id)
            
            try:
                logger.info(f"Reprocesando Lead {lead_id} ({call['nombre']} {call['apellidos']}) - Call: {call['call_id']}")
                logger.info(f"  Status actual: {call['status']}, Duration: {call['duration']}")
                
                # Si el status es None, no podemos procesar
                if call['status'] is None:
                    logger.warning(f"  Status es None, saltando lead {lead_id}")
                    processed_count += 1
                    continue
                
                # Mapear el status numérico a string (igual que hace el sistema)
                def map_pearl_status_to_result(conversation_status: int, status: int) -> str:
                    if conversation_status == 4:  # Completed conversation
                        return 'completed'
                    elif status == 4:
                        return 'completed'
                    elif status == 5:
                        return 'busy'
                    elif status == 6:
                        return 'no_answer'  # Nuevo mapeo
                    elif status == 7:
                        return 'no_answer'
                    elif status == 3:
                        return 'calling'
                    else:
                        return 'error'
                
                # Crear call_result como lo haría el sistema
                call_result = {
                    'success': call['status'] == 4,  # Simplificado
                    'status': map_pearl_status_to_result(0, call['status'] or 0),
                    'duration': call['duration'] or 0,
                    'error_message': None,
                    'lead_id': lead_id,
                    'phone_number': call['phone_number']
                }
                
                # Crear pearl_response
                pearl_response = {
                    'id': call['call_id'],
                    'to': call['phone_number'],
                    'status': call['status'],
                    'duration': call['duration'],
                    'summary': call['summary'],
                    'recordingUrl': call['recording_url'],
                    'startTime': call['call_time'].isoformat() if call['call_time'] else None
                }
                
                # Procesar con el sistema integrado
                success = enhanced_process_call_result(lead_id, call_result, pearl_response)
                
                processed_count += 1
                if success:
                    success_count += 1
                    logger.info(f"✅ Lead {lead_id} reprocesado exitosamente")
                else:
                    logger.warning(f"⚠️ Error reprocesando Lead {lead_id}")
                
            except Exception as e:
                logger.error(f"❌ Error reprocesando Lead {lead_id}: {e}")
                processed_count += 1
        
        # Resumen final
        logger.info(f"""
╔══════════════════════════════════════╗
║       REPROCESO LEADS FALLIDOS       ║
╠══════════════════════════════════════╣
║ Leads únicos procesados:       {processed_count:4d} ║
║ Exitosos:                      {success_count:4d} ║
║ Fallidos:                      {processed_count - success_count:4d} ║
╚══════════════════════════════════════╝
        """)
        
    except Exception as e:
        logger.error(f"Error en reproceso: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== REPROCESANDO LEADS FALLIDOS ===")
    print("Reprocesando leads que fallaron por errores de call_status truncation")
    print()
    
    reprocesar_leads_fallidos()
    
    print()
    print("=== REPROCESO COMPLETADO ===")
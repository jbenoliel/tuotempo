"""
Script simple para actualizar directamente los leads que fallaron
"""

import mysql.connector
import logging

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

def fix_leads_directly():
    """
    Actualiza directamente los leads que fallaron con valores apropiados.
    """
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Ver el estado actual de estos leads
        lead_ids_str = ','.join(map(str, FAILED_LEAD_IDS))
        
        cursor.execute(f"""
            SELECT 
                l.id,
                l.nombre,
                l.apellidos,
                l.telefono,
                l.call_status,
                l.call_attempts_count,
                l.last_call_attempt,
                pc.status as pearl_status,
                pc.duration,
                pc.call_time
            FROM leads l
            LEFT JOIN pearl_calls pc ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
                AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            WHERE l.id IN ({lead_ids_str})
            ORDER BY l.id, pc.call_time DESC
        """)
        
        results = cursor.fetchall()
        logger.info(f"Estado actual de {len(results)} leads:")
        
        leads_to_update = {}
        for result in results:
            lead_id = result['id']
            if lead_id not in leads_to_update:
                leads_to_update[lead_id] = result
                logger.info(f"  Lead {lead_id}: call_status={result['call_status']}, pearl_status={result['pearl_status']}, attempts={result['call_attempts_count']}")
        
        # Actualizar los leads con llamadas completadas (status 4)
        updated_count = 0
        
        for lead_id, data in leads_to_update.items():
            if data['pearl_status'] == '4':  # Completed
                logger.info(f"Actualizando Lead {lead_id} como 'completed'")
                
                cursor.execute("""
                    UPDATE leads SET
                        call_status = 'completed',
                        call_attempts_count = IFNULL(call_attempts_count, 0) + 1,
                        last_call_attempt = NOW(),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (lead_id,))
                
                updated_count += 1
            
            elif data['pearl_status'] is not None:  # Otros status
                # Mapear status según el mapeo correcto
                if data['pearl_status'] == '5':
                    new_status = 'busy'
                elif data['pearl_status'] == '6':
                    new_status = 'no_answer'
                elif data['pearl_status'] == '7':
                    new_status = 'no_answer'
                else:
                    new_status = 'error'
                
                logger.info(f"Actualizando Lead {lead_id} como '{new_status}' (pearl_status: {data['pearl_status']})")
                
                cursor.execute("""
                    UPDATE leads SET
                        call_status = %s,
                        call_attempts_count = IFNULL(call_attempts_count, 0) + 1,
                        last_call_attempt = NOW(),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (new_status, lead_id))
                
                updated_count += 1
        
        conn.commit()
        
        logger.info(f"""
╔══════════════════════════════════════╗
║         ACTUALIZACIÓN DIRECTA        ║
╠══════════════════════════════════════╣
║ Leads procesados:              {len(leads_to_update):4d} ║
║ Leads actualizados:            {updated_count:4d} ║
╚══════════════════════════════════════╝
        """)
        
        # Verificar los resultados
        cursor.execute(f"""
            SELECT id, nombre, apellidos, call_status, call_attempts_count
            FROM leads 
            WHERE id IN ({lead_ids_str})
            ORDER BY id
        """)
        
        final_results = cursor.fetchall()
        logger.info("Estado final de los leads:")
        for result in final_results:
            logger.info(f"  Lead {result['id']}: {result['nombre']} {result['apellidos']} -> {result['call_status']} (attempts: {result['call_attempts_count']})")
            
    except Exception as e:
        logger.error(f"Error en actualización directa: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== ACTUALIZACIÓN DIRECTA DE LEADS ===")
    fix_leads_directly()
    print("=== COMPLETADO ===")
"""
Script para corregir los contadores de call_attempts_count corruptos.
Los contadores actuales (643, 602, 601, etc.) son incorrectos.
Los corregiremos basándonos en el número real de llamadas de Pearl AI.
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

def corregir_contadores_llamadas():
    """
    Corrige los contadores call_attempts_count basándose en el número real de llamadas.
    """
    
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Identificar leads con contadores anómalos
        logger.info("Identificando leads con contadores anómalos...")
        
        cursor.execute("""
            SELECT id, telefono, nombre, apellidos, call_attempts_count, lead_status
            FROM leads 
            WHERE call_attempts_count > 10  -- Cualquier cosa > 10 es sospechosa
            ORDER BY call_attempts_count DESC
        """)
        
        anomalous_leads = cursor.fetchall()
        logger.info(f"Encontrados {len(anomalous_leads)} leads con contadores anómalos")
        
        if not anomalous_leads:
            logger.info("No hay contadores anómalos para corregir")
            return
        
        # 2. Corregir cada lead basándose en llamadas reales de Pearl AI
        corrected = 0
        errors = 0
        
        for lead in anomalous_leads:
            try:
                lead_id = lead['id']
                telefono = lead['telefono']
                old_count = lead['call_attempts_count']
                
                # Contar llamadas reales de Pearl AI para este teléfono
                cursor.execute("""
                    SELECT COUNT(*) as real_count
                    FROM pearl_calls 
                    WHERE REPLACE(REPLACE(phone_number, '+34', ''), ' ', '') = %s
                """, (telefono,))
                
                real_count_result = cursor.fetchone()
                real_count = real_count_result['real_count'] if real_count_result else 0
                
                # Si no hay llamadas de Pearl, usar un contador conservador basado en el estado
                if real_count == 0:
                    if lead['lead_status'] == 'closed':
                        real_count = 6  # Asumimos que se cerró por máximo intentos
                    else:
                        real_count = 1  # Lead abierto sin llamadas
                
                # Actualizar el contador
                cursor.execute("""
                    UPDATE leads 
                    SET call_attempts_count = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (real_count, lead_id))
                
                corrected += 1
                
                if corrected <= 10:  # Mostrar los primeros 10 ejemplos
                    logger.info(f"Lead {lead_id} ({lead['nombre']} {lead['apellidos']}): {old_count} -> {real_count} intentos")
                
            except Exception as e:
                logger.error(f"Error corrigiendo lead {lead_id}: {e}")
                errors += 1
        
        # 3. Commit cambios
        conn.commit()
        
        logger.info(f"""
╔══════════════════════════════════════╗
║       CORRECCION DE CONTADORES       ║
╠══════════════════════════════════════╣
║ Leads con contadores anómalos: {len(anomalous_leads):4d} ║
║ Leads corregidos:              {corrected:4d} ║  
║ Errores:                       {errors:4d} ║
╚══════════════════════════════════════╝
        """)
        
        # 4. Verificar resultado final
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN call_attempts_count IS NULL THEN 'NULL'
                    WHEN call_attempts_count <= 6 THEN '1-6 (normal)'
                    WHEN call_attempts_count <= 10 THEN '7-10 (alto)'
                    ELSE '11+ (anómalo)'
                END as rango,
                COUNT(*) as count
            FROM leads
            GROUP BY 
                CASE 
                    WHEN call_attempts_count IS NULL THEN 'NULL'
                    WHEN call_attempts_count <= 6 THEN '1-6 (normal)'
                    WHEN call_attempts_count <= 10 THEN '7-10 (alto)'
                    ELSE '11+ (anómalo)'
                END
            ORDER BY count DESC
        """)
        
        final_distribution = cursor.fetchall()
        
        logger.info("Distribución final de contadores:")
        for dist in final_distribution:
            logger.info(f"  {dist['rango']}: {dist['count']} leads")
        
    except Exception as e:
        logger.error(f"Error en corrección de contadores: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== CORRECCION DE CONTADORES DE LLAMADAS ===")
    print("Corrigiendo contadores call_attempts_count basándose en llamadas reales de Pearl AI")
    print()
    
    corregir_contadores_llamadas()
    
    print()
    print("=== CORRECCION COMPLETADA ===")
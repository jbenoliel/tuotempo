"""
Script para corregir call_status con valores inválidos en Railway
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

def fix_invalid_call_status():
    """
    Busca y corrige call_status con valores inválidos.
    """
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar leads con call_status inválidos (no son valores del ENUM)
        logger.info("Buscando leads con call_status inválidos...")
        
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, call_status 
            FROM leads 
            WHERE call_status NOT IN ('no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer')
            AND call_status IS NOT NULL
            LIMIT 100
        """)
        
        invalid_leads = cursor.fetchall()
        
        if not invalid_leads:
            logger.info("✅ No se encontraron leads con call_status inválidos")
            return
            
        logger.info(f"🔍 Encontrados {len(invalid_leads)} leads con call_status inválidos:")
        
        for lead in invalid_leads[:10]:  # Mostrar solo los primeros 10
            logger.info(f"  Lead {lead['id']}: '{lead['call_status']}'")
        
        if len(invalid_leads) > 10:
            logger.info(f"  ... y {len(invalid_leads) - 10} más")
        
        # Corregir los call_status inválidos
        logger.info("Corrigiendo call_status inválidos...")
        
        cursor.execute("""
            UPDATE leads 
            SET call_status = 'error'
            WHERE call_status NOT IN ('no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer')
            AND call_status IS NOT NULL
        """)
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        logger.info(f"✅ Corregidos {affected_rows} registros con call_status inválidos")
        
        # Verificar la distribución actual de call_status
        cursor.execute("""
            SELECT call_status, COUNT(*) as count 
            FROM leads 
            WHERE call_status IS NOT NULL
            GROUP BY call_status 
            ORDER BY count DESC
        """)
        
        distribution = cursor.fetchall()
        
        logger.info("📊 Distribución actual de call_status:")
        for row in distribution:
            logger.info(f"  {row['call_status']}: {row['count']}")
            
    except Exception as e:
        logger.error(f"Error corrigiendo call_status: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== CORRIGIENDO CALL_STATUS INVÁLIDOS ===")
    fix_invalid_call_status()
    print("=== PROCESO COMPLETADO ===")
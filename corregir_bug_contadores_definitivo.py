"""
Corrección definitiva del bug de contadores imposibles.
Resetear todos los contadores basándose en llamadas reales de Pearl AI.
"""

import mysql.connector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_railway_connection():
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def corregir_bug_definitivo():
    conn = get_railway_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Ver estado actual
        cursor.execute("""
            SELECT COUNT(*) as impossible 
            FROM leads 
            WHERE call_attempts_count > 50
        """)
        impossible = cursor.fetchone()['impossible']
        
        logger.info(f"Leads con contadores imposibles (>50): {impossible}")
        
        if impossible == 0:
            logger.info("No hay contadores imposibles para corregir")
            return
        
        # 2. Corregir TODOS los leads con contadores > 50
        cursor.execute("""
            SELECT id, telefono, call_attempts_count
            FROM leads 
            WHERE call_attempts_count > 50
            ORDER BY call_attempts_count DESC
        """)
        
        bad_leads = cursor.fetchall()
        logger.info(f"Corrigiendo {len(bad_leads)} leads...")
        
        corrected = 0
        for lead in bad_leads[:10]:  # Mostrar primeros 10
            lead_id = lead['id']
            telefono = lead['telefono']
            old_count = lead['call_attempts_count']
            
            # Contar llamadas reales
            cursor.execute("""
                SELECT COUNT(*) as real_count
                FROM pearl_calls 
                WHERE REPLACE(REPLACE(phone_number, '+34', ''), ' ', '') = %s
            """, (telefono,))
            
            result = cursor.fetchone()
            real_count = result['real_count'] if result else 0
            
            # Si no hay llamadas pero el lead está cerrado, asumir máximo (6)
            if real_count == 0:
                cursor.execute("SELECT lead_status FROM leads WHERE id = %s", (lead_id,))
                status = cursor.fetchone()
                if status and status['lead_status'] == 'closed':
                    real_count = 6
                else:
                    real_count = 0
            
            logger.info(f"Lead {lead_id}: {old_count} -> {real_count}")
            corrected += 1
        
        # 3. Aplicar corrección MASIVA a todos
        logger.info(f"Aplicando corrección masiva a {len(bad_leads)} leads...")
        
        # Resetear todos los contadores problemáticos
        cursor.execute("""
            UPDATE leads l
            SET call_attempts_count = (
                SELECT COUNT(*)
                FROM pearl_calls pc
                WHERE REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') = l.telefono
            ),
            updated_at = NOW()
            WHERE l.call_attempts_count > 50
        """)
        
        updated = cursor.rowcount
        conn.commit()
        
        # 4. Verificar resultado
        cursor.execute("""
            SELECT COUNT(*) as still_bad 
            FROM leads 
            WHERE call_attempts_count > 50
        """)
        still_bad = cursor.fetchone()['still_bad']
        
        logger.info(f"✅ Corrección aplicada:")
        logger.info(f"  Leads actualizados: {updated}")
        logger.info(f"  Leads aún problemáticos: {still_bad}")
        
        # 5. Nueva distribución
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN call_attempts_count IS NULL THEN 'NULL'
                    WHEN call_attempts_count = 0 THEN '0'
                    WHEN call_attempts_count <= 6 THEN '1-6'
                    WHEN call_attempts_count <= 10 THEN '7-10'
                    ELSE '11+'
                END as rango,
                COUNT(*) as count
            FROM leads
            GROUP BY 
                CASE 
                    WHEN call_attempts_count IS NULL THEN 'NULL'
                    WHEN call_attempts_count = 0 THEN '0'
                    WHEN call_attempts_count <= 6 THEN '1-6'
                    WHEN call_attempts_count <= 10 THEN '7-10'
                    ELSE '11+'
                END
        """)
        
        distribution = cursor.fetchall()
        logger.info("Nueva distribución:")
        for dist in distribution:
            logger.info(f"  {dist['rango']}: {dist['count']}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== CORRECCIÓN DEFINITIVA BUG CONTADORES ===")
    corregir_bug_definitivo()
    print("=== CORRECCIÓN COMPLETADA ===")
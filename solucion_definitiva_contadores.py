"""
SOLUCIÓN DEFINITIVA para corregir los 400+ contadores corruptos.
Procesamiento por lotes evitando problemas de collation.
"""

import mysql.connector
import logging
import time
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    """Conecta a Railway con configuración optimizada."""
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway',
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci',
        autocommit=False
    )

def get_corrupted_leads(conn) -> List[Dict]:
    """Obtiene todos los leads con contadores corruptos."""
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT id, telefono, call_attempts_count, lead_status
        FROM leads 
        WHERE call_attempts_count > 50
        ORDER BY call_attempts_count DESC
    """)
    
    return cursor.fetchall()

def count_real_calls(conn, telefono: str) -> int:
    """Cuenta las llamadas reales de Pearl AI para un teléfono."""
    cursor = conn.cursor(dictionary=True)
    
    # Intentar múltiples formatos para encontrar el teléfono
    formats_to_try = [
        f'+34{telefono}',  # +34611366486
        telefono,          # 611366486
        f'0034{telefono}', # 0034611366486
        f'34{telefono}'    # 34611366486
    ]
    
    max_count = 0
    for phone_format in formats_to_try:
        cursor.execute("SELECT COUNT(*) as count FROM pearl_calls WHERE phone_number = %s", (phone_format,))
        result = cursor.fetchone()
        if result and result['count'] > max_count:
            max_count = result['count']
    
    return max_count

def process_batch(conn, leads_batch: List[Dict]) -> Dict[str, int]:
    """Procesa un lote de leads y devuelve estadísticas."""
    stats = {'corrected': 0, 'errors': 0, 'total': len(leads_batch)}
    cursor = conn.cursor()
    
    for lead in leads_batch:
        try:
            lead_id = lead['id']
            telefono = lead['telefono']
            old_count = lead['call_attempts_count']
            
            # Contar llamadas reales
            real_count = count_real_calls(conn, telefono)
            
            # Si no hay llamadas pero el lead está cerrado, usar lógica de negocio
            if real_count == 0:
                if lead['lead_status'] == 'closed':
                    real_count = 6  # Asumimos que se cerró por máximo intentos
                else:
                    real_count = 0  # Lead abierto sin llamadas
            
            # Actualizar el lead
            cursor.execute("""
                UPDATE leads 
                SET call_attempts_count = %s, updated_at = NOW() 
                WHERE id = %s
            """, (real_count, lead_id))
            
            if stats['corrected'] < 5:  # Mostrar primeros 5 de cada lote
                logger.info(f"  Lead {lead_id}: {old_count} -> {real_count}")
            
            stats['corrected'] += 1
            
        except Exception as e:
            logger.error(f"Error procesando Lead {lead.get('id', '?')}: {e}")
            stats['errors'] += 1
    
    return stats

def solucion_definitiva():
    """Ejecuta la solución definitiva por lotes."""
    conn = None
    try:
        conn = get_railway_connection()
        logger.info("🔗 Conectado a Railway")
        
        # 1. Obtener todos los leads corruptos
        corrupted_leads = get_corrupted_leads(conn)
        total_corrupted = len(corrupted_leads)
        
        if total_corrupted == 0:
            logger.info("✅ No hay contadores corruptos para corregir")
            return
        
        logger.info(f"🐛 Encontrados {total_corrupted} leads con contadores corruptos")
        
        # 2. Procesar en lotes de 50 para evitar timeouts
        batch_size = 50
        total_corrected = 0
        total_errors = 0
        
        for i in range(0, total_corrupted, batch_size):
            batch_num = (i // batch_size) + 1
            total_batches = (total_corrupted + batch_size - 1) // batch_size
            
            batch = corrupted_leads[i:i + batch_size]
            
            logger.info(f"📦 Procesando lote {batch_num}/{total_batches} ({len(batch)} leads)")
            
            stats = process_batch(conn, batch)
            
            # Commit por lote
            conn.commit()
            
            total_corrected += stats['corrected']
            total_errors += stats['errors']
            
            logger.info(f"   Lote completado: {stats['corrected']} corregidos, {stats['errors']} errores")
            
            # Pausa pequeña entre lotes
            if i + batch_size < total_corrupted:
                time.sleep(0.5)
        
        # 3. Verificación final
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as remaining FROM leads WHERE call_attempts_count > 50")
        remaining = cursor.fetchone()['remaining']
        
        # 4. Nueva distribución
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN call_attempts_count IS NULL THEN 'NULL'
                    WHEN call_attempts_count = 0 THEN '0'
                    WHEN call_attempts_count <= 6 THEN '1-6 (normal)'
                    WHEN call_attempts_count <= 10 THEN '7-10 (alto)'
                    WHEN call_attempts_count <= 50 THEN '11-50 (muy alto)'
                    ELSE '51+ (corrupto)'
                END as rango,
                COUNT(*) as count
            FROM leads
            GROUP BY 
                CASE 
                    WHEN call_attempts_count IS NULL THEN 'NULL'
                    WHEN call_attempts_count = 0 THEN '0'
                    WHEN call_attempts_count <= 6 THEN '1-6 (normal)'
                    WHEN call_attempts_count <= 10 THEN '7-10 (alto)'
                    WHEN call_attempts_count <= 50 THEN '11-50 (muy alto)'
                    ELSE '51+ (corrupto)'
                END
        """)
        
        distribution = cursor.fetchall()
        
        # 5. Resumen final
        logger.info(f"""
╔══════════════════════════════════════════════════╗
║              CORRECCIÓN COMPLETADA               ║
╠══════════════════════════════════════════════════╣
║ Total leads corruptos encontrados: {total_corrupted:12d} ║
║ Leads corregidos exitosamente:     {total_corrected:12d} ║
║ Errores durante corrección:        {total_errors:12d} ║
║ Leads con contadores >50 restantes: {remaining:11d} ║
╚══════════════════════════════════════════════════╝
        """)
        
        logger.info("Nueva distribución de contadores:")
        for dist in distribution:
            logger.info(f"  {dist['rango']:15}: {dist['count']:5d} leads")
        
        if remaining == 0:
            logger.info("🎉 ¡TODOS LOS CONTADORES CORRUPTOS HAN SIDO CORREGIDOS!")
        else:
            logger.warning(f"⚠️  Quedan {remaining} contadores por corregir")
        
    except Exception as e:
        logger.error(f"💥 Error crítico: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logger.info("🔌 Conexión cerrada")

if __name__ == "__main__":
    print("=" * 60)
    print("SOLUCION DEFINITIVA - CORRECCION CONTADORES CORRUPTOS")
    print("=" * 60)
    print()
    
    solucion_definitiva()
    
    print()
    print("=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)
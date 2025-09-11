"""
Verificar qué leads tienen citas en los últimos días
"""

import mysql.connector
from datetime import datetime, timedelta
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

def verificar_citas_recientes():
    """
    Verifica leads con citas en los últimos días
    """
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Ver todos los status_level_1 que existen
        cursor.execute("""
            SELECT status_level_1, COUNT(*) as count 
            FROM leads 
            WHERE status_level_1 IS NOT NULL 
            AND status_level_1 != ''
            GROUP BY status_level_1 
            ORDER BY count DESC
        """)
        
        statuses = cursor.fetchall()
        print("Todos los status_level_1 existentes:")
        for status in statuses:
            print(f"  • {status['status_level_1']}: {status['count']}")
        
        # Buscar leads con status positivos en los últimos 7 días
        cursor.execute("""
            SELECT 
                l.id,
                l.nombre,
                l.apellidos,
                l.telefono,
                l.ciudad,
                l.status_level_1,
                l.status_level_2,
                l.updated_at,
                l.last_call_attempt
            FROM leads l
            WHERE l.status_level_1 LIKE '%Útiles Positivos%'
            OR l.status_level_1 LIKE '%Cita%'
            OR l.status_level_1 LIKE '%cita%'
            OR l.status_level_1 LIKE '%Interesado%'
            ORDER BY l.updated_at DESC
            LIMIT 20
        """)
        
        leads_positivos = cursor.fetchall()
        
        print(f"\n📈 LEADS CON STATUS POSITIVOS (últimos 20):")
        print("="*80)
        
        if not leads_positivos:
            print("No se encontraron leads con status positivos")
            return
            
        for lead in leads_positivos:
            print(f"\n🎯 LEAD {lead['id']}: {lead.get('nombre', 'N/A')} {lead.get('apellidos', 'N/A')}")
            print(f"   📞 Teléfono: {lead.get('telefono', 'N/A')}")
            print(f"   📍 Ciudad: {lead.get('ciudad', 'N/A')}")
            print(f"   📈 Status L1: {lead.get('status_level_1', 'N/A')}")
            print(f"   📋 Status L2: {lead.get('status_level_2', 'N/A')}")
            print(f"   🕐 Actualizado: {lead.get('updated_at', 'N/A')}")
            print(f"   📞 Última llamada: {lead.get('last_call_attempt', 'N/A')}")
        
        # Buscar por fechas específicas
        for dias_atras in [0, 1, 2, 3]:
            fecha = datetime.now() - timedelta(days=dias_atras)
            fecha_str = fecha.strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads 
                WHERE (status_level_1 LIKE '%Útiles Positivos%'
                       OR status_level_1 LIKE '%Cita%'
                       OR status_level_1 LIKE '%cita%')
                AND DATE(updated_at) = %s
            """, (fecha_str,))
            
            result = cursor.fetchone()
            print(f"\n📅 {fecha_str}: {result['count']} leads con cita")
            
    except Exception as e:
        logger.error(f"Error verificando citas: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verificar_citas_recientes()
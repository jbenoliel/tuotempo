#!/usr/bin/env python3
"""
Script para limpiar todos los leads marcados para llamada en Railway
"""
import os
import mysql.connector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_railway_connection():
    """Obtiene conexión directa a Railway"""
    try:
        # URL de Railway desde .env
        mysql_url = "mysql://root:YUpuOBaMqUdztuRwDvZBNsRQsucGMYur@mysql.railway.internal:3306/railway"
        
        # Parsear la URL
        # mysql://user:password@host:port/database
        url_parts = mysql_url.replace('mysql://', '').split('@')
        user_pass = url_parts[0].split(':')
        host_port_db = url_parts[1].split('/')
        host_port = host_port_db[0].split(':')
        
        connection = mysql.connector.connect(
            host=host_port[0],
            port=int(host_port[1]),
            user=user_pass[0],
            password=user_pass[1],
            database=host_port_db[1]
        )
        return connection
    except Exception as e:
        logger.error(f"Error conectando a Railway: {e}")
        return None

def limpiar_leads_seleccionados():
    """Limpia todos los leads marcados para llamada"""
    
    try:
        conn = get_railway_connection()
        if not conn:
            logger.error("No se pudo conectar a Railway")
            return
            
        cursor = conn.cursor(dictionary=True)
        
        # Ver cuántos leads están marcados actualmente
        cursor.execute("SELECT COUNT(*) AS count FROM leads WHERE selected_for_calling = 1")
        count_before = cursor.fetchone()['count']
        logger.info(f"🔍 Leads marcados actualmente en Railway: {count_before}")
        
        if count_before == 0:
            logger.info("✅ No hay leads marcados para limpiar")
            return
        
        # Mostrar algunos ejemplos de los leads marcados
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, call_status 
            FROM leads 
            WHERE selected_for_calling = 1 
            LIMIT 10
        """)
        ejemplos = cursor.fetchall()
        
        logger.info("📋 Ejemplos de leads marcados:")
        for lead in ejemplos:
            logger.info(f"  ID: {lead['id']}, Nombre: {lead.get('nombre', 'N/A')}, Tel: {lead.get('telefono', 'N/A')}, Status: {lead.get('call_status', 'N/A')}")
        
        # Limpiar automáticamente (sin confirmación para Railway)
        logger.info(f"🧹 Limpiando {count_before} leads marcados...")
        
        cursor.execute("""
            UPDATE leads 
            SET selected_for_calling = 0,
                call_status = 'no_selected'
            WHERE selected_for_calling = 1
        """)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        logger.info(f"✅ {rows_updated} leads limpiados correctamente en Railway")
        
        # Verificar que la limpieza fue exitosa
        cursor.execute("SELECT COUNT(*) AS count FROM leads WHERE selected_for_calling = 1")
        count_after = cursor.fetchone()['count']
        logger.info(f"📊 Leads marcados después de limpieza: {count_after}")
        
        # Mostrar distribución de call_status
        cursor.execute("""
            SELECT call_status, COUNT(*) AS count 
            FROM leads 
            WHERE call_status IS NOT NULL
            GROUP BY call_status 
            ORDER BY count DESC
        """)
        distribution = cursor.fetchall()
        
        logger.info("📈 Distribución de call_status después de limpieza:")
        for row in distribution:
            status = row['call_status'] or 'NULL'
            logger.info(f"  {status}: {row['count']}")
            
    except Exception as e:
        logger.error(f"❌ Error limpiando leads: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals() and conn and conn.is_connected():
            cursor.close()
            conn.close()
            logger.info("🔌 Conexión a Railway cerrada")

if __name__ == "__main__":
    limpiar_leads_seleccionados()
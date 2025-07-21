#!/usr/bin/env python3
"""
Script para limpiar todos los leads marcados para llamada
"""
from db import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def limpiar_leads_seleccionados():
    """Limpia todos los leads marcados para llamada"""
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Ver cuántos leads están marcados actualmente
        cursor.execute("SELECT COUNT(*) AS count FROM leads WHERE selected_for_calling = TRUE")
        count_before = cursor.fetchone()['count']
        logger.info(f"Leads marcados actualmente: {count_before}")
        
        if count_before == 0:
            logger.info("No hay leads marcados para limpiar")
            return
        
        # Mostrar algunos ejemplos de los leads marcados
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, call_status 
            FROM leads 
            WHERE selected_for_calling = TRUE 
            LIMIT 10
        """)
        ejemplos = cursor.fetchall()
        
        logger.info("Ejemplos de leads marcados:")
        for lead in ejemplos:
            logger.info(f"  ID: {lead['id']}, Nombre: {lead.get('nombre', 'N/A')}, Tel: {lead.get('telefono', 'N/A')}, Status: {lead.get('call_status', 'N/A')}")
        
        # Confirmar limpieza
        confirm = input(f"\n¿LIMPIAR todos los {count_before} leads marcados? (s/N): ").strip().lower()
        if confirm != 's':
            logger.info("Operación cancelada")
            return
        
        # Limpiar todos los leads
        cursor.execute("""
            UPDATE leads 
            SET selected_for_calling = FALSE,
                call_status = 'no_selected'
            WHERE selected_for_calling = TRUE
        """)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        logger.info(f"✅ {rows_updated} leads limpiados correctamente")
        
        # Verificar que la limpieza fue exitosa
        cursor.execute("SELECT COUNT(*) AS count FROM leads WHERE selected_for_calling = TRUE")
        count_after = cursor.fetchone()['count']
        logger.info(f"Leads marcados después de limpieza: {count_after}")
        
        # Mostrar distribución de call_status
        cursor.execute("""
            SELECT call_status, COUNT(*) AS count 
            FROM leads 
            GROUP BY call_status 
            ORDER BY count DESC
        """)
        distribution = cursor.fetchall()
        
        logger.info("Distribución de call_status después de limpieza:")
        for row in distribution:
            logger.info(f"  {row['call_status']}: {row['count']}")
            
    except Exception as e:
        logger.error(f"Error limpiando leads: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    limpiar_leads_seleccionados()
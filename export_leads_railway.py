#!/usr/bin/env python3
"""
Exportar leads de Railway a Excel
"""

import pandas as pd
import pymysql
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Railway (producción)
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    """Crear conexión a Railway"""
    try:
        connection = pymysql.connect(**RAILWAY_CONFIG)
        logger.info(f"✅ Conectado a Railway: {RAILWAY_CONFIG['host']}:{RAILWAY_CONFIG['port']}")
        return connection
    except Exception as e:
        logger.error(f"❌ Error conectando a Railway: {e}")
        return None

def export_leads_to_excel():
    """Exportar todos los leads a Excel"""
    connection = get_railway_connection()
    if not connection:
        return None
    
    try:
        # Query para obtener leads con cita agendada de todos los ficheros
        query = """
        SELECT 
            l.id,
            l.nombre,
            l.apellidos,
            l.telefono,
            l.telefono2,
            l.email,
            l.nif,
            l.fecha_nacimiento,
            l.sexo,
            l.ciudad,
            l.codigo_postal,
            l.nombre_clinica,
            l.direccion_clinica,
            l.certificado,
            l.poliza,
            l.segmento,
            l.conPack,
            l.cita,
            l.hora_cita,
            l.preferencia_horario,
            l.fecha_minima_reserva,
            l.status_level_1,
            l.status_level_2,
            l.ultimo_estado,
            l.resultado_llamada,
            l.hora_rellamada,
            l.call_status,
            l.call_priority,
            l.selected_for_calling,
            l.last_call_attempt,
            l.call_attempts_count,
            l.match_source as fichero_origen,
            l.updated_at
        FROM leads l
        WHERE l.status_level_1 = 'Cita Agendada'
        ORDER BY l.updated_at DESC
        """
        
        logger.info("📊 Ejecutando query para exportar leads...")
        df = pd.read_sql(query, connection)
        logger.info(f"✅ Obtenidos {len(df)} leads de Railway")
        
        # Formatear fechas
        date_columns = ['fecha_nacimiento', 'cita', 'fecha_minima_reserva', 'hora_rellamada', 'last_call_attempt', 'call_time', 'updated_at', 'last_call_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Convertir booleanos a texto más legible
        boolean_columns = ['conPack', 'selected_for_calling', 'manual_management']
        for col in boolean_columns:
            if col in df.columns:
                df[col] = df[col].map({True: 'Sí', False: 'No', 1: 'Sí', 0: 'No'}).fillna('No')
        
        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"citas_septiembre_{timestamp}.xlsx"
        
        # Exportar a Excel
        logger.info(f"📁 Guardando en {filename}...")
        df.to_excel(filename, index=False, engine='openpyxl')
        
        logger.info(f"✅ Export completado: {filename}")
        logger.info(f"📈 Total leads exportados: {len(df)}")
        
        # Estadísticas rápidas
        status_counts = df['status_level_1'].value_counts()
        logger.info("📊 Distribución por estado:")
        for status, count in status_counts.head(10).items():
            logger.info(f"  • {status}: {count}")
        
        return filename
        
    except Exception as e:
        logger.error(f"❌ Error exportando leads: {e}")
        return None
    finally:
        connection.close()
        logger.info("🔌 Conexión cerrada")

def main():
    """Función principal"""
    logger.info("🚀 Iniciando export de leads desde Railway...")
    
    filename = export_leads_to_excel()
    if filename:
        logger.info(f"🎉 Export exitoso: {filename}")
    else:
        logger.error("💥 Error en el export")

if __name__ == "__main__":
    main()
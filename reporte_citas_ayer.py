"""
Reporte detallado de leads que pidieron cita ayer con todos los datos
"""

import mysql.connector
import pandas as pd
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

def get_leads_citas_ayer():
    """
    Obtiene todos los datos de leads que pidieron cita ayer
    """
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Calcular fecha de ayer
        ayer = datetime.now() - timedelta(days=1)
        fecha_ayer = ayer.strftime('%Y-%m-%d')
        
        logger.info(f"Buscando leads que pidieron cita el {fecha_ayer}...")
        
        # Consulta para obtener leads con cita (status_level_1 positivo) del día de ayer
        cursor.execute("""
            SELECT 
                l.*,
                pc.call_id,
                pc.call_time as pearl_call_time,
                pc.duration as call_duration,
                pc.summary as call_summary,
                pc.recording_url,
                pc.transcription,
                pc.collected_info
            FROM leads l
            LEFT JOIN pearl_calls pc ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
                AND DATE(pc.call_time) = %s
            WHERE l.status_level_1 IN (
                'Útiles Positivos - Cita con pack',
                'Útiles Positivos - Cita sin pack',
                'Útiles Positivos - Interesado pero no disponible'
            )
            AND (
                DATE(l.updated_at) = %s 
                OR DATE(pc.call_time) = %s
                OR DATE(l.last_call_attempt) = %s
            )
            ORDER BY l.updated_at DESC, pc.call_time DESC
        """, (fecha_ayer, fecha_ayer, fecha_ayer, fecha_ayer))
        
        leads_citas = cursor.fetchall()
        
        if not leads_citas:
            logger.info(f"No se encontraron leads que pidieron cita el {fecha_ayer}")
            return
            
        logger.info(f"Encontrados {len(leads_citas)} registros de leads con cita del {fecha_ayer}")
        
        # Convertir a DataFrame para mejor manejo
        df = pd.DataFrame(leads_citas)
        
        # Remover duplicados por ID de lead (quedarse con el más reciente)
        df_unique = df.drop_duplicates(subset=['id'], keep='first')
        
        logger.info(f"Leads únicos con cita: {len(df_unique)}")
        
        # Mostrar resumen en consola
        print(f"\n{'='*80}")
        print(f"LEADS QUE PIDIERON CITA EL {fecha_ayer.upper()}")
        print(f"{'='*80}")
        
        for idx, lead in df_unique.iterrows():
            print(f"\n🎯 LEAD {lead['id']}: {lead.get('nombre', 'N/A')} {lead.get('apellidos', 'N/A')}")
            print(f"   📞 Teléfono: {lead.get('telefono', 'N/A')}")
            print(f"   🏢 Clínica: {lead.get('nombre_clinica', 'N/A')}")
            print(f"   📍 Ciudad: {lead.get('ciudad', 'N/A')}")
            print(f"   📧 Email: {lead.get('email', 'N/A')}")
            print(f"   📈 Status: {lead.get('status_level_1', 'N/A')}")
            print(f"   🎙️ Duración llamada: {lead.get('call_duration', 'N/A')} seg")
            print(f"   📝 Resumen: {lead.get('call_summary', 'N/A')[:100]}..." if lead.get('call_summary') else "   📝 Resumen: N/A")
            print(f"   🎵 Grabación: {'Sí' if lead.get('recording_url') else 'No'}")
            print(f"   📂 Archivo origen: {lead.get('archivo_origen', 'N/A')}")
            print(f"   🕐 Última actualización: {lead.get('updated_at', 'N/A')}")
            
        # Generar archivo Excel con todos los detalles
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_citas_detallado_{fecha_ayer.replace('-', '')}_{timestamp}.xlsx"
        
        # Preparar datos para Excel
        df_export = df_unique.copy()
        
        # Reordenar columnas importantes al principio
        cols_importantes = [
            'id', 'nombre', 'apellidos', 'telefono', 'email', 
            'nombre_clinica', 'ciudad', 'status_level_1', 'status_level_2',
            'call_duration', 'call_summary', 'recording_url', 
            'archivo_origen', 'updated_at', 'last_call_attempt'
        ]
        
        # Obtener columnas que existen
        cols_existentes = [col for col in cols_importantes if col in df_export.columns]
        cols_restantes = [col for col in df_export.columns if col not in cols_existentes]
        
        df_export = df_export[cols_existentes + cols_restantes]
        
        # Exportar a Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='Leads_Citas_Detalle', index=False)
            
            # Ajustar anchos de columna
            worksheet = writer.sheets['Leads_Citas_Detalle']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"\n{'='*80}")
        print(f"📊 ARCHIVO GENERADO: {filename}")
        print(f"   • Contiene {len(df_unique)} leads únicos con cita")
        print(f"   • Todos los campos de la tabla leads")
        print(f"   • Datos de llamadas de Pearl AI")
        print(f"   • Grabaciones y transcripciones")
        print(f"{'='*80}")
        
        # Estadísticas adicionales
        status_counts = df_unique['status_level_1'].value_counts()
        print(f"\nDistribución por tipo de cita:")
        for status, count in status_counts.items():
            print(f"   • {status}: {count}")
            
        ciudades_counts = df_unique['ciudad'].value_counts().head(5)
        print(f"\nTop 5 ciudades:")
        for ciudad, count in ciudades_counts.items():
            print(f"   • {ciudad}: {count}")
            
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    get_leads_citas_ayer()
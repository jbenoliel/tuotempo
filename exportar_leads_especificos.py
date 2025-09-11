"""
Exportar datos específicos de leads a Excel
"""

import pandas as pd
import mysql.connector
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def exportar_leads_especificos():
    """
    Exporta datos específicos de leads a Excel
    """
    # Lista de nombres para buscar
    nombres_buscar = [
        'MANUEL PANPLONA NAVARRO',
        'YENDERSON DEIVIS CHIRINOS VERA', 
        'JOSEFA DIVOLS RUIZ',
        'MARYLINE ROMAIN BURDET',
        'DARISELA CANARIO FELIZ',
        'FELIX LOPEZ MONDEJAR',
        'LUIS PABLO VALENCIANO ROZALEN',
        'MONICA LILIANA MONTEALEGRE GONZALEZ',
        'KATIA SAUDITH PEREZ FUENTES',
        'MANUEL MARTINEZ NIETO'
    ]
    
    conn = get_railway_connection()
    leads_data = []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        for nombre_completo in nombres_buscar:
            # Separar nombre y apellidos para buscar
            partes = nombre_completo.split(' ', 1)
            if len(partes) >= 2:
                nombre = partes[0]
                apellidos = partes[1]
            else:
                nombre = partes[0]
                apellidos = ''
            
            logger.info(f"Buscando: {nombre_completo}")
            
            # Buscar por nombre y apellidos
            cursor.execute("""
                SELECT * FROM leads 
                WHERE 
                    (UPPER(CONCAT(nombre, ' ', apellidos)) LIKE %s 
                     OR UPPER(CONCAT(apellidos, ' ', nombre)) LIKE %s
                     OR (UPPER(nombre) LIKE %s AND UPPER(apellidos) LIKE %s))
                ORDER BY updated_at DESC
                LIMIT 1
            """, (
                f"%{nombre_completo.upper()}%",
                f"%{nombre_completo.upper()}%", 
                f"%{nombre.upper()}%",
                f"%{apellidos.upper()}%"
            ))
            
            result = cursor.fetchone()
            
            if result:
                logger.info(f"  ✓ Encontrado: ID {result['id']} - {result.get('nombre')} {result.get('apellidos')}")
                leads_data.append(result)
            else:
                logger.warning(f"  ✗ No encontrado: {nombre_completo}")
                # Agregar fila vacía con el nombre buscado
                leads_data.append({
                    'id': None,
                    'nombre_buscado': nombre_completo,
                    'nombre': 'NO ENCONTRADO',
                    'apellidos': 'NO ENCONTRADO',
                    'telefono': None,
                    'email': None,
                    'status_level_1': None,
                    'status_level_2': None,
                    'created_at': None,
                    'updated_at': None
                })
        
        # Convertir a DataFrame
        df = pd.DataFrame(leads_data)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_especificos_{timestamp}.xlsx"
        
        # Exportar a Excel
        df.to_excel(filename, index=False)
        
        logger.info(f"""
╔══════════════════════════════════════════════════╗
║              EXPORTACIÓN COMPLETADA              ║
╠══════════════════════════════════════════════════╣
║ Nombres buscados:                         {len(nombres_buscar):2d}    ║
║ Leads encontrados:                        {len([l for l in leads_data if l.get('id')]):<2d}    ║
║ No encontrados:                           {len([l for l in leads_data if not l.get('id')]):<2d}    ║
║ Archivo generado:                                ║
║ {filename:<48} ║
╚══════════════════════════════════════════════════╝
        """)
        
        return filename
        
    except Exception as e:
        logger.error(f"Error en exportación: {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("="*60)
    print("EXPORTACIÓN DE LEADS ESPECÍFICOS")
    print("="*60)
    
    filename = exportar_leads_especificos()
    
    if filename:
        print(f"\n✓ Excel generado exitosamente: {filename}")
    else:
        print("\n✗ Error en la exportación")
    
    print("="*60)
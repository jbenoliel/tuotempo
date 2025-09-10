#!/usr/bin/env python3
"""
Script para exportar TODAS las citas modificadas ayer (ambos ficheros)
"""

import pymysql
import pandas as pd
from datetime import datetime, timedelta

# Configuracion de Railway
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    """Crear conexion a Railway"""
    return pymysql.connect(**RAILWAY_CONFIG)

def export_todas_citas_ayer():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("EXPORTANDO TODAS LAS CITAS MODIFICADAS AYER - RAILWAY")
    print("=" * 60)
    
    # Calcular fecha de ayer
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Fecha de ayer: {ayer}")
    print()
    
    # Obtener TODAS las citas modificadas ayer (ambos ficheros)
    cursor.execute(f"""
        SELECT 
            id,
            nombre,
            apellidos,
            telefono,
            email,
            status_level_1,
            status_level_2,
            lead_status,
            call_attempts_count,
            updated_at,
            origen_archivo
        FROM leads 
        WHERE DATE(updated_at) = '{ayer}'
        AND TRIM(status_level_1) = 'Cita Agendada'
        ORDER BY origen_archivo, updated_at DESC
    """)
    
    resultados = cursor.fetchall()
    
    if not resultados:
        print("No se encontraron citas modificadas ayer")
        conn.close()
        return
    
    print(f"Encontradas {len(resultados)} citas modificadas ayer")
    
    # Mostrar resumen por fichero
    print("\nResumen por fichero:")
    cursor.execute(f"""
        SELECT 
            origen_archivo,
            COUNT(*) as cantidad
        FROM leads 
        WHERE DATE(updated_at) = '{ayer}'
        AND TRIM(status_level_1) = 'Cita Agendada'
        GROUP BY origen_archivo
        ORDER BY cantidad DESC
    """)
    
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} citas")
    
    # Crear DataFrame
    columnas = [
        'ID', 'Nombre', 'Apellidos', 'Telefono', 'Email', 
        'Status Level 1', 'Status Level 2', 'Lead Status',
        'Call Attempts', 'Updated At', 'Origen Archivo'
    ]
    
    data = []
    for row in resultados:
        data.append(list(row))
    
    df = pd.DataFrame(data, columns=columnas)
    
    # Crear nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"todas_citas_modificadas_ayer_{timestamp}.xlsx"
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Todas Citas Ayer', index=False)
        
        # Formatear la hoja
        worksheet = writer.sheets['Todas Citas Ayer']
        
        # Ajustar ancho de columnas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Máximo 50
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"\nArchivo generado: {filename}")
    print(f"Registros exportados: {len(resultados)}")
    
    # Mostrar detalle completo por fichero
    print(f"\nDetalle completo:")
    
    # Septiembre
    septiembre_leads = [row for row in resultados if row[10] == 'Septiembre']
    if septiembre_leads:
        print(f"\nSEPTIEMBRE ({len(septiembre_leads)} citas):")
        for i, row in enumerate(septiembre_leads):
            print(f"  {i+1}. ID:{row[0]:4d} | {row[1]:20s} | {row[3]:12s} | {row[6]} | {row[9]}")
    
    # SEGURCAIXA_JULIO
    segurcaixa_leads = [row for row in resultados if row[10] == 'SEGURCAIXA_JULIO']
    if segurcaixa_leads:
        print(f"\nSEGURCAIXA_JULIO ({len(segurcaixa_leads)} citas):")
        for i, row in enumerate(segurcaixa_leads):
            print(f"  {i+1}. ID:{row[0]:4d} | {row[1]:20s} | {row[3]:12s} | {row[6]} | {row[9]}")
    
    print(f"\nTOTAL: {len(resultados)} citas modificadas ayer")
    
    conn.close()

if __name__ == "__main__":
    export_todas_citas_ayer()
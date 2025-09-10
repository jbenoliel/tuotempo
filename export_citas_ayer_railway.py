#!/usr/bin/env python3
"""
Script para exportar leads SEGURCAIXA_JULIO modificados ayer que querían cita
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

def export_citas_ayer():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("EXPORTANDO LEADS CON CITA MODIFICADOS AYER - RAILWAY")
    print("=" * 55)
    
    # Calcular fecha de ayer
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Fecha de ayer: {ayer}")
    print()
    
    # Primero verificar columnas disponibles
    cursor.execute("DESCRIBE leads")
    columnas_db = [col[0] for col in cursor.fetchall()]
    print(f"Columnas disponibles: {columnas_db[:10]}...")  # Mostrar primeras 10
    print()
    
    # Obtener leads que querían cita y fueron modificados ayer
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
            closure_reason,
            call_attempts_count,
            updated_at,
            origen_archivo,
            preferences,
            desired_date_1,
            desired_time_1,
            desired_date_2,
            desired_time_2,
            desired_date_3,
            desired_time_3,
            observaciones
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) = '{ayer}'
        AND TRIM(status_level_1) = 'Cita Agendada'
        ORDER BY updated_at DESC
    """)
    
    resultados = cursor.fetchall()
    
    if not resultados:
        print("No se encontraron leads con cita modificados ayer")
        conn.close()
        return
    
    print(f"Encontrados {len(resultados)} leads con cita modificados ayer")
    
    # Crear DataFrame
    columnas = [
        'ID', 'Nombre', 'Apellidos', 'Telefono', 'Email', 
        'Status Level 1', 'Status Level 2', 'Lead Status', 'Closure Reason',
        'Call Attempts', 'Updated At', 'Origen Archivo',
        'Preferences', 'Desired Date 1', 'Desired Time 1',
        'Desired Date 2', 'Desired Time 2', 'Desired Date 3', 'Desired Time 3',
        'Observaciones'
    ]
    
    data = []
    for row in resultados:
        data.append(list(row))
    
    df = pd.DataFrame(data, columns=columnas)
    
    # Crear nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"leads_citas_modificados_ayer_{timestamp}.xlsx"
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Leads Citas Ayer', index=False)
        
        # Formatear la hoja
        worksheet = writer.sheets['Leads Citas Ayer']
        
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
    
    # Mostrar resumen por tipo de cita
    print(f"\nResumen por tipo de cita:")
    cursor.execute(f"""
        SELECT 
            status_level_2,
            COUNT(*) as cantidad
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) = '{ayer}'
        AND TRIM(status_level_1) = 'Cita Agendada'
        GROUP BY status_level_2
        ORDER BY cantidad DESC
    """)
    
    for row in cursor.fetchall():
        tipo_cita = row[0] or 'Sin especificar'
        cantidad = row[1]
        print(f"  - {tipo_cita}: {cantidad}")
    
    # Mostrar algunos ejemplos
    print(f"\nEjemplos de leads exportados:")
    for i, row in enumerate(resultados[:5]):
        print(f"  {i+1}. {row[1]} {row[2] or ''} | {row[3]} | {row[5]} | {row[6]} | {row[10]}")
    
    if len(resultados) > 5:
        print(f"  ... y {len(resultados) - 5} mas")
    
    conn.close()

if __name__ == "__main__":
    export_citas_ayer()
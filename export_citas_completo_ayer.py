#!/usr/bin/env python3
"""
Script para exportar TODAS las citas modificadas ayer con preferencias completas
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

def export_citas_completo():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("EXPORTANDO TODAS LAS CITAS CON PREFERENCIAS - RAILWAY")
    print("=" * 60)
    
    # Calcular fecha de ayer
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Fecha de ayer: {ayer}")
    print()
    
    # Verificar campos disponibles relacionados con preferencias
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'railway' 
        AND TABLE_NAME = 'leads' 
        AND (COLUMN_NAME LIKE '%preference%' 
             OR COLUMN_NAME LIKE '%fecha%' 
             OR COLUMN_NAME LIKE '%date%' 
             OR COLUMN_NAME LIKE '%time%'
             OR COLUMN_NAME LIKE '%hora%'
             OR COLUMN_NAME LIKE '%mañana%'
             OR COLUMN_NAME LIKE '%tarde%'
             OR COLUMN_NAME LIKE '%desired%')
    """)
    
    campos_disponibles = [row[0] for row in cursor.fetchall()]
    print(f"Campos disponibles relacionados con fechas/horarios: {campos_disponibles}")
    print()
    
    # Obtener TODAS las citas modificadas ayer con todos los campos posibles
    query = f"""
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
            origen_archivo"""
    
    # Añadir campos de preferencias si existen
    campos_extra = []
    posibles_campos = ['preference_time', 'preferred_time', 'preferencia_horario', 'fecha_minima', 'fecha_cita', 
                      'desired_date_1', 'desired_time_1', 'desired_date_2', 'desired_time_2', 'desired_date_3', 'desired_time_3',
                      'preferences', 'observaciones', 'notas', 'fecha_minima_reserva']
    
    for campo in posibles_campos:
        if campo in campos_disponibles:
            query += f",\n            {campo}"
            campos_extra.append(campo)
    
    query += f"""
        FROM leads 
        WHERE DATE(updated_at) = '{ayer}'
        AND TRIM(status_level_1) = 'Cita Agendada'
        ORDER BY origen_archivo, updated_at DESC
    """
    
    print(f"Campos extra que se incluiran: {campos_extra}")
    print()
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if not resultados:
        print("No se encontraron citas modificadas ayer")
        conn.close()
        return
    
    print(f"Encontradas {len(resultados)} citas modificadas ayer")
    
    # Crear columnas para DataFrame
    columnas = [
        'ID', 'Nombre', 'Apellidos', 'Telefono', 'Email', 
        'Status Level 1', 'Status Level 2', 'Lead Status',
        'Call Attempts', 'Updated At', 'Origen Archivo'
    ]
    
    # Añadir columnas extra
    for campo in campos_extra:
        columnas.append(campo.replace('_', ' ').title())
    
    # Crear DataFrame
    data = []
    for row in resultados:
        data.append(list(row))
    
    df = pd.DataFrame(data, columns=columnas)
    
    # Crear nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"citas_completas_ayer_{timestamp}.xlsx"
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Citas Completas', index=False)
        
        # Formatear la hoja
        worksheet = writer.sheets['Citas Completas']
        
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
    print(f"Columnas incluidas: {len(columnas)}")
    
    # Mostrar detalle con preferencias
    print(f"\nDetalle completo con preferencias:")
    
    base_cols = 11  # numero de columnas basicas
    
    for i, row in enumerate(resultados):
        nombre = row[1] or ''
        telefono = row[3] or ''
        fichero = row[10] or ''
        fecha_update = row[9] or ''
        
        print(f"\n{i+1:2d}. {nombre:20s} | {telefono:12s} | {fichero}")
        print(f"    Actualizado: {fecha_update}")
        
        # Mostrar campos extra si existen
        if len(row) > base_cols:
            for j, campo in enumerate(campos_extra):
                valor = row[base_cols + j] if (base_cols + j) < len(row) else None
                if valor:
                    print(f"    {campo}: {valor}")
    
    conn.close()

if __name__ == "__main__":
    export_citas_completo()
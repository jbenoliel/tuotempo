#!/usr/bin/env python3
"""
REPORTE DIARIO DE CITAS - Para uso diario
Script para exportar todas las citas conseguidas el día anterior
Incluye: preferencias de horario, fecha mínima de reserva y todos los datos de contacto

COMO USAR:
1. Ejecutar desde venv: ./venv/Scripts/python.exe reporte_citas_diario.py
2. El script exportará las citas del día anterior automáticamente
3. Genera un archivo Excel con todas las preferencias y fechas
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

def generar_reporte_diario():
    """Generar reporte diario de citas del día anterior"""
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    # Calcular fecha de ayer
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    print("REPORTE DIARIO DE CITAS - RAILWAY")
    print("=" * 50)
    print(f"Generando reporte para: {ayer}")
    print(f"Fecha de generación: {hoy}")
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
             OR COLUMN_NAME LIKE '%desired%')
    """)
    
    campos_disponibles = [row[0] for row in cursor.fetchall()]
    
    # Construir query con campos básicos
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
    posibles_campos = ['preferencia_horario', 'fecha_minima_reserva', 'hora_cita', 
                      'observaciones', 'notas', 'desired_date_1', 'desired_time_1']
    
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
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    if not resultados:
        print(f"No se encontraron citas para el día {ayer}")
        print("El reporte estará vacío.")
        conn.close()
        return
    
    print(f"Encontradas {len(resultados)} citas para {ayer}")
    
    # Mostrar resumen por fichero
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
    
    print("\nResumen por fichero:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} citas")
    
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
    
    # Crear nombre de archivo con fecha
    fecha_str = datetime.strptime(ayer, '%Y-%m-%d').strftime('%d-%m-%Y')
    filename = f"reporte_citas_{fecha_str}.xlsx"
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=f'Citas {fecha_str}', index=False)
        
        # Formatear la hoja
        worksheet = writer.sheets[f'Citas {fecha_str}']
        
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
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"\nArchivo generado: {filename}")
    print(f"Registros exportados: {len(resultados)}")
    print(f"Columnas incluidas: {len(columnas)}")
    
    # Mostrar detalle resumido
    print(f"\nDetalle de citas conseguidas el {ayer}:")
    
    base_cols = 11  # numero de columnas basicas
    
    for i, row in enumerate(resultados):
        nombre = (row[1] or '').strip()
        apellidos = (row[2] or '').strip()
        nombre_completo = f"{nombre} {apellidos}".strip()
        telefono = row[3] or ''
        fichero = row[10] or ''
        hora = str(row[9]).split()[-1] if row[9] else ''  # Solo la hora
        
        print(f"{i+1:2d}. {nombre_completo:25s} | {telefono:12s} | {fichero:15s} | {hora}")
        
        # Mostrar preferencias si existen
        if len(row) > base_cols:
            preferencias = []
            for j, campo in enumerate(campos_extra):
                valor = row[base_cols + j] if (base_cols + j) < len(row) else None
                if valor:
                    if campo == 'preferencia_horario':
                        preferencias.append(f"Pref: {valor}")
                    elif campo == 'fecha_minima_reserva':
                        preferencias.append(f"Desde: {valor}")
            if preferencias:
                print(f"     {' | '.join(preferencias)}")
    
    print(f"\nTOTAL: {len(resultados)} citas conseguidas el {ayer}")
    print(f"Archivo Excel: {filename}")
    print()
    print("NOTA: Ejecutar este script diariamente para obtener el reporte de citas del día anterior")
    
    conn.close()

if __name__ == "__main__":
    try:
        generar_reporte_diario()
    except Exception as e:
        print(f"Error ejecutando reporte: {e}")
        print("Verificar conexión a Railway y configuración")
#!/usr/bin/env python3
"""
Script para verificar el estado de la tabla de programaciones de llamadas
"""

import pymysql
from datetime import datetime

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

def verificar_programaciones():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("ESTADO DE PROGRAMACIONES DE LLAMADAS - RAILWAY")
    print("=" * 55)
    print(f"Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar si existe la tabla de programaciones
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'railway' 
        AND (TABLE_NAME LIKE '%call%' 
             OR TABLE_NAME LIKE '%programacion%'
             OR TABLE_NAME LIKE '%schedule%'
             OR TABLE_NAME LIKE '%queue%')
    """)
    
    tablas_relacionadas = cursor.fetchall()
    print("Tablas relacionadas con llamadas/programaciones:")
    for tabla in tablas_relacionadas:
        print(f"  - {tabla[0]}")
    
    if not tablas_relacionadas:
        print("  No se encontraron tablas específicas de programaciones")
    
    print()
    
    # Verificar campos en la tabla leads relacionados con programaciones
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'railway' 
        AND TABLE_NAME = 'leads' 
        AND (COLUMN_NAME LIKE '%call%' 
             OR COLUMN_NAME LIKE '%programacion%'
             OR COLUMN_NAME LIKE '%schedule%'
             OR COLUMN_NAME LIKE '%queue%'
             OR COLUMN_NAME LIKE '%next%'
             OR COLUMN_NAME LIKE '%hora%'
             OR COLUMN_NAME LIKE '%rellamada%')
    """)
    
    campos_programacion = cursor.fetchall()
    print("Campos de programación en tabla 'leads':")
    for campo in campos_programacion:
        print(f"  - {campo[0]}: {campo[1]}")
    print()
    
    # Verificar leads programados para llamar
    if campos_programacion:
        # Buscar leads con hora_rellamada programada
        cursor.execute("""
            SELECT COUNT(*) FROM leads 
            WHERE hora_rellamada IS NOT NULL
            AND status_level_1 = 'Volver a llamar'
        """)
        con_hora_rellamada = cursor.fetchone()[0]
        print(f"Leads con hora_rellamada programada: {con_hora_rellamada}")
        
        # Leads programados para hoy
        hoy = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(f"""
            SELECT COUNT(*) FROM leads 
            WHERE DATE(hora_rellamada) = '{hoy}'
            AND status_level_1 = 'Volver a llamar'
        """)
        programados_hoy = cursor.fetchone()[0]
        print(f"Leads programados para hoy: {programados_hoy}")
        
        # Leads vencidos (pasada la hora)
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(f"""
            SELECT COUNT(*) FROM leads 
            WHERE hora_rellamada < '{ahora}'
            AND status_level_1 = 'Volver a llamar'
        """)
        vencidos = cursor.fetchone()[0]
        print(f"Leads vencidos (hora pasada): {vencidos}")
        
        # Leads futuros
        cursor.execute(f"""
            SELECT COUNT(*) FROM leads 
            WHERE hora_rellamada > '{ahora}'
            AND status_level_1 = 'Volver a llamar'
        """)
        futuros = cursor.fetchone()[0]
        print(f"Leads programados a futuro: {futuros}")
        print()
        
        # Ejemplos de programaciones
        print("Ejemplos de leads programados:")
        cursor.execute(f"""
            SELECT id, nombre, telefono, status_level_1, status_level_2, hora_rellamada, origen_archivo
            FROM leads 
            WHERE hora_rellamada IS NOT NULL
            AND status_level_1 = 'Volver a llamar'
            ORDER BY hora_rellamada DESC
            LIMIT 10
        """)
        
        ejemplos = cursor.fetchall()
        for ejemplo in ejemplos:
            print(f"  ID:{ejemplo[0]:4d} | {ejemplo[1]:20s} | {ejemplo[2]:12s} | {ejemplo[6]:15s} | {ejemplo[5]}")
        
        if len(ejemplos) == 0:
            print("  No hay leads con programaciones activas")
    
    print()
    
    # Resumen por fichero de origen
    print("Resumen por fichero de origen (solo 'Volver a llamar'):")
    cursor.execute("""
        SELECT 
            origen_archivo,
            COUNT(*) as total,
            COUNT(CASE WHEN hora_rellamada IS NOT NULL THEN 1 END) as con_programacion,
            COUNT(CASE WHEN hora_rellamada IS NULL THEN 1 END) as sin_programacion
        FROM leads 
        WHERE status_level_1 = 'Volver a llamar'
        GROUP BY origen_archivo
        ORDER BY total DESC
    """)
    
    resumen = cursor.fetchall()
    for row in resumen:
        fichero = row[0] or 'Sin origen'
        total = row[1]
        con_prog = row[2]
        sin_prog = row[3]
        print(f"  {fichero:20s}: {total:3d} total | {con_prog:3d} programados | {sin_prog:3d} sin programar")
    
    conn.close()

if __name__ == "__main__":
    verificar_programaciones()
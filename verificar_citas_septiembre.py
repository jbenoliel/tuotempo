#!/usr/bin/env python3
"""
Script para verificar citas en fichero Septiembre vs SEGURCAIXA_JULIO
"""

import pymysql
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

def verificar_citas():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("VERIFICACION DE CITAS POR FICHERO - RAILWAY")
    print("=" * 50)
    
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Fecha de ayer: {ayer}")
    print()
    
    # Citas totales por fichero
    print("CITAS TOTALES POR FICHERO:")
    cursor.execute("""
        SELECT 
            origen_archivo,
            status_level_1,
            status_level_2,
            COUNT(*) as cantidad
        FROM leads 
        WHERE TRIM(status_level_1) = 'Cita Agendada'
        GROUP BY origen_archivo, status_level_1, status_level_2
        ORDER BY origen_archivo, cantidad DESC
    """)
    
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]}: {row[3]}")
    
    print()
    
    # Citas modificadas ayer por fichero
    print("CITAS MODIFICADAS AYER POR FICHERO:")
    cursor.execute(f"""
        SELECT 
            origen_archivo,
            status_level_1,
            status_level_2,
            COUNT(*) as cantidad
        FROM leads 
        WHERE TRIM(status_level_1) = 'Cita Agendada'
        AND DATE(updated_at) = '{ayer}'
        GROUP BY origen_archivo, status_level_1, status_level_2
        ORDER BY origen_archivo, cantidad DESC
    """)
    
    modificadas_ayer = cursor.fetchall()
    for row in modificadas_ayer:
        print(f"  {row[0]} | {row[1]} | {row[2]}: {row[3]}")
    
    if not modificadas_ayer:
        print("  No hay citas modificadas ayer")
    
    print()
    
    # Detalle de Septiembre con cita
    print("DETALLE SEPTIEMBRE CON CITA:")
    cursor.execute("""
        SELECT 
            id, nombre, telefono, status_level_1, status_level_2, updated_at
        FROM leads 
        WHERE origen_archivo = 'Septiembre'
        AND TRIM(status_level_1) = 'Cita Agendada'
        ORDER BY updated_at DESC
    """)
    
    septiembre_citas = cursor.fetchall()
    for row in septiembre_citas:
        print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    print(f"\nTotal Septiembre con cita: {len(septiembre_citas)}")
    
    # Detalle de SEGURCAIXA_JULIO con cita
    print("\nDETALLE SEGURCAIXA_JULIO CON CITA:")
    cursor.execute("""
        SELECT 
            id, nombre, telefono, status_level_1, status_level_2, updated_at
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
        AND TRIM(status_level_1) = 'Cita Agendada'
        ORDER BY updated_at DESC
    """)
    
    segurcaixa_citas = cursor.fetchall()
    for row in segurcaixa_citas:
        print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    print(f"\nTotal SEGURCAIXA_JULIO con cita: {len(segurcaixa_citas)}")
    
    # Verificar si las de Septiembre fueron modificadas ayer
    print(f"\nSEPTIEMBRE MODIFICADAS AYER ({ayer}):")
    cursor.execute(f"""
        SELECT 
            id, nombre, telefono, status_level_1, status_level_2, updated_at
        FROM leads 
        WHERE origen_archivo = 'Septiembre'
        AND TRIM(status_level_1) = 'Cita Agendada'
        AND DATE(updated_at) = '{ayer}'
        ORDER BY updated_at DESC
    """)
    
    septiembre_ayer = cursor.fetchall()
    for row in septiembre_ayer:
        print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    print(f"\nSeptiembre con cita modificadas ayer: {len(septiembre_ayer)}")
    
    conn.close()

if __name__ == "__main__":
    verificar_citas()
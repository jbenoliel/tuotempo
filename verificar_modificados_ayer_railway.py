#!/usr/bin/env python3
"""
Script para verificar leads SEGURCAIXA_JULIO no en 'Volver a llamar' que NO fueron modificados ayer
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

def verificar_modificados():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("VERIFICACION LEADS NO MODIFICADOS AYER - RAILWAY")
    print("=" * 50)
    
    # Calcular fecha de ayer
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Fecha de ayer: {ayer}")
    print()
    
    # Verificar qué campos de fecha existen
    cursor.execute("DESCRIBE leads")
    campos = cursor.fetchall()
    print("Campos de fecha disponibles:")
    for campo in campos:
        if 'date' in campo[0].lower() or 'time' in campo[0].lower() or 'updated' in campo[0].lower() or 'created' in campo[0].lower() or 'modified' in campo[0].lower():
            print(f"  - {campo[0]}: {campo[1]}")
    print()
    
    # Total actual SEGURCAIXA_JULIO
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
    """)
    total_actual = cursor.fetchone()[0]
    print(f"Total actual SEGURCAIXA_JULIO: {total_actual}")
    
    # En 'Volver a llamar'
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND TRIM(status_level_1) = 'Volver a llamar'
    """)
    volver_llamar = cursor.fetchone()[0]
    print(f"En 'Volver a llamar': {volver_llamar}")
    
    # NO en 'Volver a llamar'
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
    """)
    no_volver_llamar = cursor.fetchone()[0]
    print(f"NO en 'Volver a llamar': {no_volver_llamar}")
    
    # Verificar si existe campo updated_at o similar
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'railway' 
        AND TABLE_NAME = 'leads' 
        AND (COLUMN_NAME LIKE '%updated%' OR COLUMN_NAME LIKE '%modified%' OR COLUMN_NAME LIKE '%date%' OR COLUMN_NAME LIKE '%time%')
    """)
    
    date_fields = cursor.fetchall()
    print(f"Campos de fecha encontrados: {[field[0] for field in date_fields]}")
    
    # Intentar con updated_at si existe
    try:
        # NO en 'Volver a llamar' Y NO modificados ayer
        cursor.execute(f"""
            SELECT COUNT(*) FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
            AND DATE(updated_at) != '{ayer}'
        """)
        no_modificados_ayer = cursor.fetchone()[0]
        print(f"NO en 'Volver a llamar' Y NO modificados ayer: {no_modificados_ayer}")
        
        # Los que SÍ fueron modificados ayer
        cursor.execute(f"""
            SELECT COUNT(*) FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
            AND DATE(updated_at) = '{ayer}'
        """)
        modificados_ayer = cursor.fetchone()[0]
        print(f"NO en 'Volver a llamar' PERO modificados ayer: {modificados_ayer}")
        print()
        
        print("RESUMEN:")
        print(f"- Se MANTENDRIAN: {volver_llamar} (en 'Volver a llamar') + {modificados_ayer} (modificados ayer) = {volver_llamar + modificados_ayer}")
        print(f"- Se ELIMINARIAN: {no_modificados_ayer} (NO en 'Volver a llamar' Y NO modificados ayer)")
        print()
        
        # Ejemplos de los que se eliminarían
        cursor.execute(f"""
            SELECT id, nombre, telefono, status_level_1, status_level_2, updated_at
            FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
            AND DATE(updated_at) != '{ayer}'
            LIMIT 10
        """)
        
        print("Ejemplos de leads que se ELIMINARIAN:")
        for row in cursor.fetchall():
            print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
        
        # Ejemplos de los que se mantendrían (modificados ayer)
        cursor.execute(f"""
            SELECT id, nombre, telefono, status_level_1, status_level_2, updated_at
            FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
            AND DATE(updated_at) = '{ayer}'
            LIMIT 10
        """)
        
        print(f"\nEjemplos de leads NO en 'Volver a llamar' pero que se MANTENDRIAN (modificados ayer):")
        for row in cursor.fetchall():
            print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
            
    except Exception as e:
        print(f"Error consultando updated_at: {e}")
        
        # Intentar con created_at
        try:
            cursor.execute(f"""
                SELECT COUNT(*) FROM leads 
                WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
                AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
                AND DATE(created_at) != '{ayer}'
            """)
            no_creados_ayer = cursor.fetchone()[0]
            print(f"NO en 'Volver a llamar' Y NO creados ayer: {no_creados_ayer}")
            
        except Exception as e2:
            print(f"Error con created_at: {e2}")
            print("No se puede determinar la fecha de modificacion")
    
    conn.close()

if __name__ == "__main__":
    verificar_modificados()
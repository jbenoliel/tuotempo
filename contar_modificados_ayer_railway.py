#!/usr/bin/env python3
"""
Script para contar leads SEGURCAIXA_JULIO modificados ayer
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

def contar_modificados():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("CONTEO LEADS SEGURCAIXA_JULIO MODIFICADOS AYER")
    print("=" * 50)
    
    # Calcular fecha de ayer
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    hoy = datetime.now().strftime('%Y-%m-%d')
    print(f"Fecha de ayer: {ayer}")
    print(f"Fecha de hoy: {hoy}")
    print()
    
    # Total SEGURCAIXA_JULIO
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
    """)
    total_segurcaixa = cursor.fetchone()[0]
    print(f"Total leads SEGURCAIXA_JULIO: {total_segurcaixa}")
    
    # Modificados ayer
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) = '{ayer}'
    """)
    modificados_ayer = cursor.fetchone()[0]
    print(f"Modificados ayer ({ayer}): {modificados_ayer}")
    
    # Modificados hoy
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) = '{hoy}'
    """)
    modificados_hoy = cursor.fetchone()[0]
    print(f"Modificados hoy ({hoy}): {modificados_hoy}")
    
    # No modificados ni ayer ni hoy
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) != '{ayer}' 
        AND DATE(updated_at) != '{hoy}'
    """)
    no_modificados_reciente = cursor.fetchone()[0]
    print(f"NO modificados ayer ni hoy: {no_modificados_reciente}")
    
    # Desglose por estado de los modificados ayer
    print(f"\nDesglose de los {modificados_ayer} modificados ayer:")
    cursor.execute(f"""
        SELECT 
            IFNULL(status_level_1, 'NULL') as status1,
            IFNULL(status_level_2, 'NULL') as status2,
            COUNT(*) as cantidad
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) = '{ayer}'
        GROUP BY status_level_1, status_level_2
        ORDER BY cantidad DESC
    """)
    
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]}: {row[2]}")
    
    # Ejemplos de modificados ayer
    print(f"\nEjemplos de leads modificados ayer:")
    cursor.execute(f"""
        SELECT id, nombre, telefono, status_level_1, status_level_2, updated_at
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND DATE(updated_at) = '{ayer}'
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    print(f"\nRESUMEN:")
    print(f"- Modificados ayer: {modificados_ayer}")
    print(f"- Modificados hoy: {modificados_hoy}")
    print(f"- No modificados reciente: {no_modificados_reciente}")
    print(f"- Total: {modificados_ayer + modificados_hoy + no_modificados_reciente} = {total_segurcaixa}")
    
    conn.close()

if __name__ == "__main__":
    contar_modificados()
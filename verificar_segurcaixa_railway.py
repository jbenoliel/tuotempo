#!/usr/bin/env python3
"""
Script para verificar conteos de leads SEGURCAIXA_JULIO en Railway
"""

import pymysql

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

def verificar_conteos():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("VERIFICACION DE LEADS SEGURCAIXA_JULIO - RAILWAY")
    print("=" * 50)
    
    # Total SEGURCAIXA_JULIO
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
    """)
    total_segurcaixa = cursor.fetchone()[0]
    print(f"Total leads SEGURCAIXA_JULIO: {total_segurcaixa}")
    
    # SEGURCAIXA_JULIO en 'Volver a llamar'
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND TRIM(status_level_1) = 'Volver a llamar'
    """)
    volver_llamar_count = cursor.fetchone()[0]
    print(f"En 'Volver a llamar': {volver_llamar_count}")
    
    # SEGURCAIXA_JULIO NO en 'Volver a llamar' 
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
    """)
    no_volver_llamar_count = cursor.fetchone()[0]
    print(f"NO en 'Volver a llamar': {no_volver_llamar_count}")
    
    print(f"Verificacion: {volver_llamar_count} + {no_volver_llamar_count} = {volver_llamar_count + no_volver_llamar_count}")
    
    # Desglose por estados
    print(f"\nDesglose de estados SEGURCAIXA_JULIO:")
    cursor.execute("""
        SELECT 
            IFNULL(status_level_1, 'NULL') as status1,
            IFNULL(status_level_2, 'NULL') as status2,
            COUNT(*) as cantidad
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
        GROUP BY status_level_1, status_level_2
        ORDER BY cantidad DESC
    """)
    
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]}: {row[2]}")
    
    # Estados que se eliminarian
    print(f"\nEjemplos de leads que se ELIMINARIAN:")
    cursor.execute("""
        SELECT id, nombre, telefono, status_level_1, status_level_2, lead_status, closure_reason
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(f"  ID:{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]}")
    
    print(f"\nRESUMEN:")
    print(f"- Se MANTENDRAN: {volver_llamar_count} leads (estado 'Volver a llamar')")
    print(f"- Se ELIMINARAN: {no_volver_llamar_count} leads (otros estados)")
    
    conn.close()

if __name__ == "__main__":
    verificar_conteos()
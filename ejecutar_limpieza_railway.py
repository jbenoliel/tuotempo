#!/usr/bin/env python3
"""
Script para ejecutar la limpieza de leads SEGURCAIXA_JULIO en Railway
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

def ejecutar_limpieza():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("EJECUTANDO LIMPIEZA SEGURCAIXA_JULIO - RAILWAY")
    print("=" * 50)
    
    # 1. Crear backup de la tabla leads
    print("1. Creando backup de la tabla leads...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table_name = f"leads_backup_{timestamp}"
    
    try:
        cursor.execute(f"""
            CREATE TABLE {backup_table_name} AS 
            SELECT * FROM leads
        """)
        
        cursor.execute(f"SELECT COUNT(*) FROM {backup_table_name}")
        backup_count = cursor.fetchone()[0]
        print(f"   BACKUP CREADO: {backup_table_name} con {backup_count} registros")
        
    except Exception as e:
        print(f"   ERROR creando backup: {e}")
        conn.close()
        return
    
    # 2. Ejecutar eliminacion
    print("\n2. Ejecutando eliminacion...")
    try:
        cursor.execute("""
            DELETE FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        """)
        
        eliminados = cursor.rowcount
        conn.commit()
        
        print(f"   ELIMINADOS: {eliminados} registros")
        
    except Exception as e:
        print(f"   ERROR eliminando: {e}")
        conn.rollback()
        conn.close()
        return
    
    # 3. Verificacion final
    print("\n3. Verificacion final...")
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
    """)
    final_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND TRIM(status_level_1) = 'Volver a llamar'
    """)
    final_volver_llamar = cursor.fetchone()[0]
    
    print(f"   Leads SEGURCAIXA_JULIO restantes: {final_count}")
    print(f"   Todos en 'Volver a llamar': {final_volver_llamar}")
    print(f"   Backup disponible: {backup_table_name}")
    
    if final_count == final_volver_llamar:
        print("\n   SUCCESS: Limpieza completada correctamente")
        print(f"   Se eliminaron {eliminados} leads")
        print(f"   Se mantuvieron {final_count} leads en 'Volver a llamar'")
    else:
        print(f"\n   WARNING: Los numeros no coinciden")
        print(f"   Restantes: {final_count}, En 'Volver a llamar': {final_volver_llamar}")
    
    conn.close()

if __name__ == "__main__":
    ejecutar_limpieza()
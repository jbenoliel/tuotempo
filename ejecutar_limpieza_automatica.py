#!/usr/bin/env python3
"""
Script para ejecutar automáticamente la limpieza de leads SEGURCAIXA_JULIO
modificados ANTES del 8 Sept 18h (sin confirmación manual)
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

def ejecutar_limpieza_automatica():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("EJECUTANDO LIMPIEZA AUTOMATICA SEGURCAIXA_JULIO")
    print("=" * 55)
    
    fecha_limite = '2025-09-08 18:00:00'
    print(f"Eliminando leads modificados ANTES del: {fecha_limite}")
    print("Criterios: NO en 'Volver a llamar' Y modificados ANTES del 8 Sept 2025 18:00h")
    print()
    
    # 1. Crear backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table = f"leads_backup_auto_{timestamp}"
    
    cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM leads")
    cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
    backup_count = cursor.fetchone()[0]
    print(f"1. Backup creado: {backup_table} con {backup_count} registros")
    
    # 2. Contar eliminaciones
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        AND updated_at <= '{fecha_limite}'
    """)
    para_eliminar = cursor.fetchone()[0]
    print(f"2. Para eliminar: {para_eliminar} registros")
    
    # 3. Ejecutar eliminación
    cursor.execute(f"""
        DELETE FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        AND updated_at <= '{fecha_limite}'
    """)
    
    eliminados = cursor.rowcount
    conn.commit()
    print(f"3. ELIMINADOS: {eliminados} registros")
    
    # 4. Verificación final
    cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO'")
    final_total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND TRIM(status_level_1) = 'Volver a llamar'
    """)
    final_volver_llamar = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        AND updated_at > '{fecha_limite}'
    """)
    final_recientes = cursor.fetchone()[0]
    
    print(f"\n4. RESULTADO FINAL:")
    print(f"   - Total SEGURCAIXA_JULIO: {final_total}")
    print(f"   - En 'Volver a llamar': {final_volver_llamar}")
    print(f"   - Otros (modificados después Sept 8 18h): {final_recientes}")
    print(f"   - Backup disponible: {backup_table}")
    
    if eliminados == para_eliminar:
        print(f"\n   SUCCESS: Limpieza completada")
        print(f"   Se eliminaron {eliminados} leads antiguos de SEGURCAIXA_JULIO")
    else:
        print(f"\n   WARNING: Discrepancia - esperaba eliminar {para_eliminar}, eliminados {eliminados}")
    
    conn.close()

if __name__ == "__main__":
    ejecutar_limpieza_automatica()
#!/usr/bin/env python3
"""
Script para restaurar la tabla leads desde el backup en Railway
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

def restaurar_backup():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("RESTAURANDO BACKUP DE LEADS - RAILWAY")
    print("=" * 50)
    
    backup_table = "leads_backup_20250910_101311"
    
    # 1. Verificar backup existe
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
        backup_count = cursor.fetchone()[0]
        print(f"1. Backup encontrado: {backup_table} con {backup_count} registros")
    except Exception as e:
        print(f"ERROR: No se encontro el backup {backup_table}: {e}")
        conn.close()
        return
    
    # 2. Verificar estado actual
    cursor.execute("SELECT COUNT(*) FROM leads")
    current_count = cursor.fetchone()[0]
    print(f"2. Estado actual tabla leads: {current_count} registros")
    
    # 3. Vaciar tabla actual
    print("3. Vaciando tabla leads actual...")
    try:
        cursor.execute("DELETE FROM leads")
        deleted = cursor.rowcount
        print(f"   Eliminados: {deleted} registros")
    except Exception as e:
        print(f"ERROR vaciando tabla: {e}")
        conn.rollback()
        conn.close()
        return
    
    # 4. Restaurar desde backup
    print("4. Restaurando datos desde backup...")
    try:
        cursor.execute(f"""
            INSERT INTO leads 
            SELECT * FROM {backup_table}
        """)
        restored = cursor.rowcount
        conn.commit()
        print(f"   Restaurados: {restored} registros")
    except Exception as e:
        print(f"ERROR restaurando: {e}")
        conn.rollback()
        conn.close()
        return
    
    # 5. Verificacion final
    print("5. Verificacion final...")
    cursor.execute("SELECT COUNT(*) FROM leads")
    final_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO'")
    segurcaixa_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'Septiembre'")
    septiembre_count = cursor.fetchone()[0]
    
    print(f"   Total leads restaurados: {final_count}")
    print(f"   Leads SEGURCAIXA_JULIO: {segurcaixa_count}")
    print(f"   Leads Septiembre: {septiembre_count}")
    
    if final_count == backup_count:
        print("\n   SUCCESS: Restauracion completada correctamente")
        print(f"   Todos los {backup_count} registros han sido restaurados")
    else:
        print(f"\n   WARNING: Discrepancia en numeros")
        print(f"   Backup: {backup_count}, Restaurados: {final_count}")
    
    # 6. Mostrar desglose por estado SEGURCAIXA_JULIO
    print("\n6. Desglose SEGURCAIXA_JULIO restaurado:")
    cursor.execute("""
        SELECT 
            IFNULL(status_level_1, 'NULL') as status1,
            COUNT(*) as cantidad
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
        GROUP BY status_level_1
        ORDER BY cantidad DESC
    """)
    
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    restaurar_backup()
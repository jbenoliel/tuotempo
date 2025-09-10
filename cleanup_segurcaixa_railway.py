#!/usr/bin/env python3
"""
Script para limpiar leads de SEGURCAIXA_JULIO que no estan en estado 'Volver a llamar'
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

def main():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("LIMPIEZA DE LEADS SEGURCAIXA_JULIO - RAILWAY")
    print("=" * 50)
    
    # 1. Crear backup de la tabla leads
    print("1. Creando backup de la tabla leads...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table_name = f"leads_backup_{timestamp}"
    
    cursor.execute(f"""
        CREATE TABLE {backup_table_name} AS 
        SELECT * FROM leads
    """)
    
    cursor.execute(f"SELECT COUNT(*) FROM {backup_table_name}")
    backup_count = cursor.fetchone()[0]
    print(f"   Backup creado: {backup_table_name} con {backup_count} registros")
    
    # 2. Verificar conteos actuales
    print("\n2. Verificando conteos actuales...")
    
    # Total SEGURCAIXA_JULIO
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO'
    """)
    total_segurcaixa = cursor.fetchone()[0]
    print(f"   Total leads SEGURCAIXA_JULIO: {total_segurcaixa}")
    
    # SEGURCAIXA_JULIO en 'Volver a llamar'
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND TRIM(status_level_1) = 'Volver a llamar'
    """)
    volver_llamar_count = cursor.fetchone()[0]
    print(f"   SEGURCAIXA_JULIO en 'Volver a llamar': {volver_llamar_count}")
    
    # SEGURCAIXA_JULIO NO en 'Volver a llamar'
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
    """)
    no_volver_llamar_count = cursor.fetchone()[0]
    print(f"   SEGURCAIXA_JULIO NO en 'Volver a llamar': {no_volver_llamar_count}")
    
    print(f"\n   Verificacion: {volver_llamar_count} + {no_volver_llamar_count} = {volver_llamar_count + no_volver_llamar_count} (debe ser {total_segurcaixa})")
    
    if volver_llamar_count != 696:
        print(f"\n   ATENCION: Esperabas 696 en 'Volver a llamar' pero hay {volver_llamar_count}")
        response = input("   Continuar de todas formas? (s/n): ")
        if response.lower() != 's':
            print("   Operacion cancelada")
            conn.close()
            return
    
    # 3. Mostrar algunos ejemplos de lo que se va a eliminar
    print("\n3. Ejemplos de registros que se eliminaran:")
    cursor.execute("""
        SELECT id, nombre, telefono1, status_level_1, status_level_2, lead_status, closure_reason
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        LIMIT 5
    """)
    
    ejemplos = cursor.fetchall()
    for ejemplo in ejemplos:
        print(f"   ID: {ejemplo[0]}, Nombre: {ejemplo[1]}, Tel: {ejemplo[2]}, Status1: {ejemplo[3]}, Status2: {ejemplo[4]}, Lead Status: {ejemplo[5]}, Closure: {ejemplo[6]}")
    
    if no_volver_llamar_count > 5:
        print(f"   ... y {no_volver_llamar_count - 5} mas")
    
    # 4. Confirmacion final
    print(f"\n4. CONFIRMACION FINAL:")
    print(f"   Se eliminaran {no_volver_llamar_count} leads de SEGURCAIXA_JULIO")
    print(f"   Se mantendran {volver_llamar_count} leads en estado 'Volver a llamar'")
    print(f"   Backup disponible en tabla: {backup_table_name}")
    
    confirm = input("\n   CONFIRMAS LA ELIMINACION? (escribe 'ELIMINAR' para confirmar): ")
    
    if confirm != 'ELIMINAR':
        print("   Operacion cancelada")
        conn.close()
        return
    
    # 5. Ejecutar eliminacion
    print("\n5. Ejecutando eliminacion...")
    cursor.execute("""
        DELETE FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
    """)
    
    eliminados = cursor.rowcount
    conn.commit()
    
    print(f"   Eliminados: {eliminados} registros")
    
    # 6. Verificacion final
    print("\n6. Verificacion final...")
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
    print(f"   Leads en 'Volver a llamar': {final_volver_llamar}")
    print(f"   Backup disponible: {backup_table_name}")
    
    if final_count == final_volver_llamar == volver_llamar_count:
        print("\n   SUCCESS: Limpieza completada correctamente")
    else:
        print("\n   WARNING: Los numeros no coinciden, revisar")
    
    conn.close()

if __name__ == "__main__":
    main()
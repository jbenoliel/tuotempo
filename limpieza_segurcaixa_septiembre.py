#!/usr/bin/env python3
"""
Script para eliminar leads SEGURCAIXA_JULIO que NO estén en 'Volver a llamar' 
y cuya fecha de modificación sea anterior al 1 de septiembre de 2025
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

def verificar_y_eliminar():
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("LIMPIEZA SEGURCAIXA_JULIO - POSTERIORES AL 8 SEPTIEMBRE 18H")
    print("=" * 60)
    
    fecha_limite = '2025-09-08 18:00:00'
    print(f"Eliminando leads modificados ANTES del: {fecha_limite}")
    print("Criterios: NO en 'Volver a llamar' Y modificados ANTES del 8 Sept 2025 18:00h")
    print()
    
    # 1. Crear backup automático
    print("1. Creando backup...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table = f"leads_backup_sept_{timestamp}"
    
    try:
        cursor.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM leads")
        cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
        backup_count = cursor.fetchone()[0]
        print(f"   Backup creado: {backup_table} con {backup_count} registros")
    except Exception as e:
        print(f"   ERROR creando backup: {e}")
        conn.close()
        return
    
    # 2. Verificar conteos actuales
    print("\n2. Verificando estado actual...")
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo = 'SEGURCAIXA_JULIO'")
    total_segurcaixa = cursor.fetchone()[0]
    print(f"   Total SEGURCAIXA_JULIO: {total_segurcaixa}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND TRIM(status_level_1) = 'Volver a llamar'
    """)
    volver_llamar = cursor.fetchone()[0]
    print(f"   En 'Volver a llamar': {volver_llamar}")
    
    # 3. Contar los que se van a eliminar
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        AND updated_at <= '{fecha_limite}'
    """)
    para_eliminar = cursor.fetchone()[0]
    print(f"   Para ELIMINAR (NO 'Volver a llamar' + modificados ANTES/EN Sept 8 18h): {para_eliminar}")
    
    # 4. Contar los que se van a mantener (NO en volver a llamar pero modificados después del 8 sept 18h)
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        AND updated_at > '{fecha_limite}'
    """)
    mantener_recientes = cursor.fetchone()[0]
    print(f"   Para MANTENER (NO 'Volver a llamar' pero modificados DESPUÉS Sept 8 18h): {mantener_recientes}")
    
    total_esperado = volver_llamar + mantener_recientes
    print(f"   Total que quedará: {total_esperado}")
    
    if para_eliminar == 0:
        print("\n   No hay registros para eliminar con estos criterios")
        conn.close()
        return
    
    # 5. Mostrar ejemplos de lo que se eliminará
    print(f"\n3. Ejemplos de registros que se ELIMINARAN ({para_eliminar} total):")
    cursor.execute(f"""
        SELECT id, nombre, telefono, status_level_1, status_level_2, updated_at
        FROM leads 
        WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
        AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
        AND updated_at <= '{fecha_limite}'
        ORDER BY updated_at DESC
        LIMIT 10
    """)
    
    ejemplos = cursor.fetchall()
    for ejemplo in ejemplos:
        print(f"   ID:{ejemplo[0]:4d} | {ejemplo[1]:20s} | {ejemplo[2]:12s} | {ejemplo[3]} | {ejemplo[4]} | {ejemplo[5]}")
    
    if len(ejemplos) == 10 and para_eliminar > 10:
        print(f"   ... y {para_eliminar - 10} registros más")
    
    # 6. Mostrar ejemplos de lo que se mantendrá (modificados después del 8 sept 18h)
    if mantener_recientes > 0:
        print(f"\n4. Ejemplos que se MANTENDRAN (modificados DESPUÉS Sept 8 18h):")
        cursor.execute(f"""
            SELECT id, nombre, telefono, status_level_1, status_level_2, updated_at
            FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
            AND updated_at > '{fecha_limite}'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        for ejemplo in cursor.fetchall():
            print(f"   ID:{ejemplo[0]:4d} | {ejemplo[1]:20s} | {ejemplo[2]:12s} | {ejemplo[3]} | {ejemplo[4]} | {ejemplo[5]}")
    
    # 7. Confirmación
    print(f"\n5. RESUMEN DE LA OPERACION:")
    print(f"   - Total actual SEGURCAIXA_JULIO: {total_segurcaixa}")
    print(f"   - Se eliminaran: {para_eliminar} (NO 'Volver a llamar' + modificados ANTES Sept 8 18h)")
    print(f"   - Se mantendran: {volver_llamar} ('Volver a llamar') + {mantener_recientes} (modificados DESPUÉS Sept 8 18h)")
    print(f"   - Total final esperado: {total_esperado}")
    print(f"   - Backup disponible: {backup_table}")
    
    respuesta = input(f"\nCONFIRMA ELIMINAR {para_eliminar} REGISTROS? (escribe 'ELIMINAR'): ")
    
    if respuesta != 'ELIMINAR':
        print("Operacion cancelada")
        conn.close()
        return
    
    # 8. Ejecutar eliminación
    print(f"\n6. Ejecutando eliminacion de {para_eliminar} registros...")
    try:
        cursor.execute(f"""
            DELETE FROM leads 
            WHERE origen_archivo = 'SEGURCAIXA_JULIO' 
            AND (TRIM(status_level_1) != 'Volver a llamar' OR status_level_1 IS NULL)
            AND updated_at <= '{fecha_limite}'
        """)
        
        eliminados = cursor.rowcount
        conn.commit()
        print(f"   ELIMINADOS: {eliminados} registros")
        
    except Exception as e:
        print(f"   ERROR eliminando: {e}")
        conn.rollback()
        conn.close()
        return
    
    # 9. Verificación final
    print(f"\n7. Verificacion final...")
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
    
    print(f"   Total SEGURCAIXA_JULIO final: {final_total}")
    print(f"   En 'Volver a llamar': {final_volver_llamar}")
    print(f"   Otros modificados DESPUÉS Sept 8 18h: {final_recientes}")
    print(f"   Backup disponible: {backup_table}")
    
    if final_total == total_esperado and eliminados == para_eliminar:
        print(f"\n   SUCCESS: Eliminacion completada correctamente")
        print(f"   Eliminados: {eliminados} registros antiguos")
        print(f"   Conservados: {final_total} registros")
    else:
        print(f"\n   WARNING: Verificar numeros")
        print(f"   Esperado: {total_esperado}, Actual: {final_total}")
        print(f"   Esperado eliminar: {para_eliminar}, Eliminados: {eliminados}")
    
    conn.close()

if __name__ == "__main__":
    verificar_y_eliminar()
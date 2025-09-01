#!/usr/bin/env python3
"""
Script para verificar si hay leads en la base de datos
"""

from db import get_connection

def verificar_leads():
    """Verificar leads en la base de datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar total de leads
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total_count = cursor.fetchone()['total']
        print(f"Total leads en BD: {total_count}")
        
        if total_count == 0:
            print("No hay leads en la base de datos")
            return False
        
        # Verificar leads con teléfono válido
        cursor.execute("""
            SELECT COUNT(*) as total FROM leads 
            WHERE ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
        """)
        with_phone = cursor.fetchone()['total']
        print(f"Leads con telefono valido: {with_phone}")
        
        # Verificar leads NO gestionados manualmente
        cursor.execute("""
            SELECT COUNT(*) as total FROM leads 
            WHERE (manual_management IS NULL OR manual_management = FALSE)
        """)
        not_manual = cursor.fetchone()['total']
        print(f"Leads NO gestionados manualmente: {not_manual}")
        
        # Verificar leads que pasan todos los filtros (como en la API)
        cursor.execute("""
            SELECT COUNT(*) as total FROM leads 
            WHERE ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
            AND (manual_management IS NULL OR manual_management = FALSE)
        """)
        api_eligible = cursor.fetchone()['total']
        print(f"Leads elegibles para API: {api_eligible}")
        
        # Mostrar algunos leads de ejemplo
        if api_eligible > 0:
            cursor.execute("""
                SELECT id, nombre, apellidos, telefono, telefono2, call_status, selected_for_calling,
                       status_level_1, status_level_2, manual_management
                FROM leads 
                WHERE ((telefono IS NOT NULL AND telefono != '') OR (telefono2 IS NOT NULL AND telefono2 != ''))
                AND (manual_management IS NULL OR manual_management = FALSE)
                LIMIT 5
            """)
            examples = cursor.fetchall()
            
            print(f"\n📋 Ejemplos de leads elegibles:")
            for lead in examples:
                print(f"  ID {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                print(f"    Tel: {lead['telefono']} | Tel2: {lead['telefono2']}")
                print(f"    Status: {lead['call_status']} | Selected: {lead['selected_for_calling']}")
                print(f"    Estado1: {lead['status_level_1']} | Estado2: {lead['status_level_2']}")
                print(f"    Manual: {lead['manual_management']}")
                print()
        
        return api_eligible > 0
        
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_tablas():
    """Verificar que las tablas necesarias existen"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar tabla leads
        cursor.execute("SHOW TABLES LIKE 'leads'")
        if cursor.fetchone():
            print("✅ Tabla 'leads' existe")
        else:
            print("❌ Tabla 'leads' NO existe")
            return False
            
        # Verificar estructura de tabla leads
        cursor.execute("DESCRIBE leads")
        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]
        
        required_columns = ['id', 'nombre', 'apellidos', 'telefono', 'telefono2', 
                          'call_status', 'selected_for_calling', 'manual_management']
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            print(f"❌ Columnas faltantes en tabla leads: {missing_columns}")
            return False
        else:
            print("✅ Todas las columnas necesarias están presentes")
            
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    print("VERIFICANDO ESTADO DE LA BASE DE DATOS")
    print("="*50)
    
    # 1. Verificar tablas
    if not verificar_tablas():
        print("\n❌ Problema con las tablas de la base de datos")
        return
    
    # 2. Verificar leads
    if verificar_leads():
        print(f"\n✅ Hay leads disponibles en la base de datos")
        print(f"\n💡 Si la API sigue devolviendo 0 leads, el problema puede ser:")
        print(f"   - Error de conexión a la BD")
        print(f"   - Filtros muy restrictivos")
        print(f"   - Error en la consulta SQL")
    else:
        print(f"\n❌ NO hay leads disponibles")
        print(f"\n💡 Soluciones:")
        print(f"   1. Cargar datos con: python recargar_excel.py")
        print(f"   2. O importar leads desde un archivo Excel")
        print(f"   3. O revisar si hay datos pero con filtros muy restrictivos")

if __name__ == "__main__":
    main()
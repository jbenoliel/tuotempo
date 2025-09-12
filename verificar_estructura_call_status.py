#!/usr/bin/env python3
"""
Script para verificar la estructura del campo call_status en la BD
"""
import pymysql
from config import settings

def verificar_estructura():
    """Verificar la estructura del campo call_status"""
    connection = None
    try:
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            print("VERIFICANDO ESTRUCTURA DE CAMPO call_status")
            print("="*50)
            
            # 1. Obtener la definición completa de la tabla leads
            cursor.execute("SHOW CREATE TABLE leads")
            result = cursor.fetchone()
            create_table = result['Create Table']
            
            # Buscar la línea del call_status
            print("1. DEFINICIÓN DEL CAMPO call_status:")
            lines = create_table.split('\n')
            for line in lines:
                if 'call_status' in line.lower():
                    print(f"   {line.strip()}")
                    
            print("\n2. INFORMACIÓN DETALLADA DE LA COLUMNA:")
            cursor.execute("DESCRIBE leads")
            columns = cursor.fetchall()
            
            for col in columns:
                if col['Field'] == 'call_status':
                    print(f"   Field: {col['Field']}")
                    print(f"   Type: {col['Type']}")
                    print(f"   Null: {col['Null']}")
                    print(f"   Key: {col['Key']}")
                    print(f"   Default: {col['Default']}")
                    print(f"   Extra: {col['Extra']}")
                    
            print("\n3. VALORES ACTUALES EN LA BD:")
            cursor.execute("""
                SELECT call_status, COUNT(*) as count 
                FROM leads 
                WHERE call_status IS NOT NULL 
                GROUP BY call_status 
                ORDER BY count DESC 
                LIMIT 10
            """)
            
            status_counts = cursor.fetchall()
            if status_counts:
                for row in status_counts:
                    print(f"   '{row['call_status']}': {row['count']} registros")
            else:
                print("   (No hay valores de call_status en la BD)")
                
            print("\n4. LEADS CON PROBLEMAS (call_status que podrían ser inválidos):")
            cursor.execute("""
                SELECT id, call_status, telefono, updated_at
                FROM leads 
                WHERE call_status IS NOT NULL 
                AND call_status NOT IN ('no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer')
                LIMIT 5
            """)
            
            invalid_status = cursor.fetchall()
            if invalid_status:
                for row in invalid_status:
                    print(f"   Lead {row['id']}: call_status='{row['call_status']}', tel={row['telefono']}")
            else:
                print("   (No se encontraron call_status inválidos)")
                
            print("\n5. VERIFICAR ALGUNOS LEADS PROBLEMÁTICOS:")
            problem_leads = [2013, 2085, 2113, 2164, 2192]  # Los mencionados en el error
            for lead_id in problem_leads:
                cursor.execute("""
                    SELECT id, call_status, telefono 
                    FROM leads 
                    WHERE id = %s
                """, (lead_id,))
                
                lead = cursor.fetchone()
                if lead:
                    print(f"   Lead {lead['id']}: call_status='{lead['call_status']}', tel={lead['telefono']}")
                else:
                    print(f"   Lead {lead_id}: (No encontrado)")
                    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    verificar_estructura()
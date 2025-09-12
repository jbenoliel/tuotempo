#!/usr/bin/env python3
"""
Script para simular la API de selección directamente con la BD
"""
import pymysql
from config import settings

def simular_api_seleccion():
    """Simular exactamente lo que hace la API select-by-status"""
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
            print("SIMULANDO API select-by-status PARA 'Volver a llamar'")
            print("="*55)
            
            # Parámetros de la API
            status_field = "status_level_1"
            status_value = "Volver a llamar"
            selected = True
            
            print(f"Parámetros: {status_field} = '{status_value}', selected = {selected}")
            
            # Construir las condiciones EXACTAS de la API
            where_conditions = [f"TRIM({status_field}) = %s"]
            params = [status_value]
            
            # CRÍTICO: Solo leads OPEN - NO seleccionar leads cerrados
            where_conditions.append("(lead_status IS NULL OR TRIM(lead_status) = 'open')")
            
            # CRÍTICO: Excluir leads con cita programada
            where_conditions.append("(status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')")
            
            where_clause = ' AND '.join(where_conditions)
            
            print(f"\n1. CONDICIONES WHERE:")
            print(f"   {where_clause}")
            print(f"   params = {params}")
            
            # Primero, contar cuántos coincidirían
            count_query = f"""
                SELECT COUNT(*) as total
                FROM leads 
                WHERE {where_clause}
            """
            
            print(f"\n2. CONTANDO LEADS QUE COINCIDEN:")
            print(f"   Query: {count_query}")
            cursor.execute(count_query, params)
            total_matches = cursor.fetchone()['total']
            print(f"   Resultado: {total_matches} leads coinciden")
            
            if total_matches == 0:
                print("\n❌ PROBLEMA IDENTIFICADO: NO HAY LEADS QUE COINCIDAN")
                print("Vamos a investigar cada condición por separado...")
                
                # Probar cada condición por separado
                print("\n3. ANALIZANDO CADA CONDICIÓN:")
                
                # Solo la condición principal
                cursor.execute(f"SELECT COUNT(*) as total FROM leads WHERE TRIM({status_field}) = %s", [status_value])
                con_estado = cursor.fetchone()['total']
                print(f"   a) Solo TRIM({status_field}) = '{status_value}': {con_estado} leads")
                
                # + condición de lead_status
                cursor.execute(f"""
                    SELECT COUNT(*) as total FROM leads 
                    WHERE TRIM({status_field}) = %s 
                    AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
                """, [status_value])
                con_estado_y_open = cursor.fetchone()['total']
                print(f"   b) + lead_status abierto: {con_estado_y_open} leads")
                
                # + condición de cita programada
                cursor.execute(f"""
                    SELECT COUNT(*) as total FROM leads 
                    WHERE TRIM({status_field}) = %s 
                    AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
                    AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
                """, [status_value])
                todas_condiciones = cursor.fetchone()['total']
                print(f"   c) + sin cita programada: {todas_condiciones} leads")
                
                # Mostrar ejemplos de leads que sí tienen "Volver a llamar" pero están open
                print("\n4. EJEMPLOS DE LEADS OPEN CON 'Volver a llamar':")
                cursor.execute(f"""
                    SELECT id, telefono, nombre, apellidos, lead_status, status_level_2, selected_for_calling
                    FROM leads 
                    WHERE TRIM({status_field}) = %s 
                    AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
                    LIMIT 3
                """, [status_value])
                
                ejemplos = cursor.fetchall()
                for lead in ejemplos:
                    sel_status = "SI" if lead['selected_for_calling'] else "NO"
                    print(f"      ID {lead['id']}: {lead['telefono']} - selected={sel_status}")
                    print(f"        lead_status='{lead['lead_status']}', status_level_2='{lead['status_level_2']}'")
                
            else:
                print(f"\n✅ HAY {total_matches} LEADS QUE DEBERÍAN SELECCIONARSE")
                
                # Simular el UPDATE
                update_query = f"""
                    UPDATE leads 
                    SET selected_for_calling = %s, 
                        updated_at = NOW()
                    WHERE {where_clause}
                """
                
                print(f"\n3. SIMULANDO UPDATE:")
                print(f"   Query: {update_query}")
                print(f"   Parámetros: [{1 if selected else 0}] + {params}")
                
                # EJECUTAR EL UPDATE
                print("\n¿Ejecutar el UPDATE? (y/N):")
                # respuesta = input().strip().lower()
                respuesta = "y"  # Auto-confirmar para la prueba
                print(f"Respuesta auto: {respuesta}")
                
                if respuesta == 'y':
                    cursor.execute(update_query, [1 if selected else 0] + params)
                    affected_count = cursor.rowcount
                    connection.commit()
                    
                    print(f"\n✅ UPDATE EJECUTADO: {affected_count} leads actualizados")
                    
                    # Verificar algunos ejemplos
                    cursor.execute(f"""
                        SELECT id, telefono, nombre, apellidos, selected_for_calling
                        FROM leads 
                        WHERE {where_clause}
                        AND selected_for_calling = 1
                        LIMIT 5
                    """, params)
                    
                    seleccionados = cursor.fetchall()
                    print(f"\nEJEMPLOS DE LEADS AHORA SELECCIONADOS:")
                    for lead in seleccionados:
                        print(f"   ID {lead['id']}: {lead['telefono']} - {lead['nombre']} {lead['apellidos']}")
                else:
                    print("UPDATE cancelado")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    simular_api_seleccion()
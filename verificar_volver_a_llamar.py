#!/usr/bin/env python3
"""
Script para verificar por qué no se seleccionan leads con "Volver a llamar"
"""
import pymysql
from config import settings

def verificar_volver_a_llamar():
    """Verificar el estado de leads con 'Volver a llamar'"""
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
            print("VERIFICANDO LEADS CON 'Volver a llamar'")
            print("="*50)
            
            # 1. Contar TODOS los leads con "Volver a llamar"
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
            """)
            total_volver_llamar = cursor.fetchone()['total']
            print(f"1. TOTAL leads con 'Volver a llamar': {total_volver_llamar}")
            
            # 2. Contar los que DEBERÍAN seleccionarse (aplicando todas las condiciones de la API)
            cursor.execute("""
                SELECT COUNT(*) as seleccionables
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
                AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
                AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
            """)
            seleccionables = cursor.fetchone()['seleccionables']
            print(f"2. Leads SELECCIONABLES: {seleccionables}")
            
            # 3. ¿Cuántos están cerrados?
            cursor.execute("""
                SELECT COUNT(*) as cerrados
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
                AND TRIM(lead_status) = 'closed'
            """)
            cerrados = cursor.fetchone()['cerrados']
            print(f"3. Leads CERRADOS: {cerrados}")
            
            # 4. ¿Cuántos tienen "Cita programada" en level_2?
            cursor.execute("""
                SELECT COUNT(*) as con_cita_programada
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
                AND TRIM(status_level_2) = 'Cita programada'
            """)
            con_cita_programada = cursor.fetchone()['con_cita_programada']
            print(f"4. Con 'Cita programada' en level_2: {con_cita_programada}")
            
            # 5. Mostrar breakdown detallado
            print("\n5. BREAKDOWN DETALLADO:")
            cursor.execute("""
                SELECT 
                    COALESCE(lead_status, 'NULL') as lead_status,
                    COALESCE(status_level_2, 'NULL') as status_level_2,
                    COUNT(*) as cantidad
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
                GROUP BY lead_status, status_level_2
                ORDER BY cantidad DESC
            """)
            
            breakdown = cursor.fetchall()
            for row in breakdown:
                print(f"   lead_status='{row['lead_status']}', status_level_2='{row['status_level_2']}': {row['cantidad']} leads")
            
            # 6. Mostrar algunos ejemplos de leads que NO se seleccionarían
            print("\n6. EJEMPLOS DE LEADS NO SELECCIONABLES:")
            cursor.execute("""
                SELECT id, telefono, nombre, apellidos, lead_status, status_level_1, status_level_2
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
                AND NOT ((lead_status IS NULL OR TRIM(lead_status) = 'open')
                    AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada'))
                LIMIT 5
            """)
            
            no_seleccionables = cursor.fetchall()
            if no_seleccionables:
                for lead in no_seleccionables:
                    print(f"   ID {lead['id']}: {lead['telefono']} - {lead['nombre']} {lead['apellidos']}")
                    print(f"      lead_status='{lead['lead_status']}', level_2='{lead['status_level_2']}'")
            else:
                print("   (No hay leads no seleccionables)")
            
            # 7. Mostrar algunos ejemplos de leads que SÍ se seleccionarían
            print("\n7. EJEMPLOS DE LEADS SELECCIONABLES:")
            cursor.execute("""
                SELECT id, telefono, nombre, apellidos, lead_status, status_level_1, status_level_2, selected_for_calling
                FROM leads 
                WHERE TRIM(status_level_1) = 'Volver a llamar'
                AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
                AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
                LIMIT 5
            """)
            
            seleccionables_ejemplos = cursor.fetchall()
            if seleccionables_ejemplos:
                for lead in seleccionables_ejemplos:
                    selected_status = "✓" if lead['selected_for_calling'] else "✗"
                    print(f"   {selected_status} ID {lead['id']}: {lead['telefono']} - {lead['nombre']} {lead['apellidos']}")
                    print(f"      lead_status='{lead['lead_status']}', level_2='{lead['status_level_2']}'")
            else:
                print("   (No hay leads seleccionables - ESTE ES EL PROBLEMA!)")
            
            # 8. PROBLEMA ESPECÍFICO: Leads con "Cita programada" que deberían estar cerrados
            print("\n8. PROBLEMA: Leads con 'Cita programada' que deberían estar cerrados:")
            cursor.execute("""
                SELECT COUNT(*) as problema
                FROM leads 
                WHERE TRIM(status_level_2) = 'Cita programada'
                AND (lead_status IS NULL OR TRIM(lead_status) != 'closed')
            """)
            
            problema_citas = cursor.fetchone()['problema']
            print(f"   Leads con 'Cita programada' pero NO cerrados: {problema_citas}")
            
            if problema_citas > 0:
                cursor.execute("""
                    SELECT id, telefono, nombre, apellidos, status_level_1, lead_status
                    FROM leads 
                    WHERE TRIM(status_level_2) = 'Cita programada'
                    AND (lead_status IS NULL OR TRIM(lead_status) != 'closed')
                    LIMIT 5
                """)
                
                ejemplos_problema = cursor.fetchall()
                print("   Ejemplos:")
                for lead in ejemplos_problema:
                    print(f"      ID {lead['id']}: {lead['telefono']} - level_1='{lead['status_level_1']}', lead_status='{lead['lead_status']}'")
            
            print("\n" + "="*50)
            print("RESUMEN:")
            print(f"- Total 'Volver a llamar': {total_volver_llamar}")
            print(f"- Deberían seleccionarse: {seleccionables}")
            print(f"- Diferencia: {total_volver_llamar - seleccionables}")
            
            if seleccionables == 0 and total_volver_llamar > 0:
                print("\n❌ PROBLEMA IDENTIFICADO: NO hay leads seleccionables")
                print("Razones posibles:")
                print(f"   - {cerrados} están cerrados (correcto si tienen cita)")
                print(f"   - {con_cita_programada} tienen 'Cita programada' (deberían estar cerrados)")
            elif seleccionables > 0:
                print(f"\n✅ Hay {seleccionables} leads que deberían poder seleccionarse")
                print("Si no se seleccionan, el problema está en otro lado")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    verificar_volver_a_llamar()
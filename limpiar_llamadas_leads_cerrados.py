#!/usr/bin/env python3
"""
Script para limpiar llamadas programadas para leads cerrados
y probar las nuevas reglas de negocio
"""
import pymysql
from datetime import datetime
from config import settings
from reprogramar_llamadas_simple import cleanup_closed_leads_schedules, cancel_scheduled_calls_for_lead

def get_connection():
    """Obtiene conexión con pymysql"""
    try:
        return pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Error conectando: {e}")
        return None

def mostrar_estado_actual():
    """Muestra el estado actual de llamadas programadas vs leads cerrados"""
    print("ESTADO ACTUAL DE LLAMADAS PROGRAMADAS")
    print("=" * 40)
    
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Estadísticas por estado de lead
            cursor.execute("""
                SELECT 
                    COALESCE(l.lead_status, 'NULL/open') as estado_lead,
                    COUNT(cs.id) as llamadas_programadas
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                GROUP BY l.lead_status
                ORDER BY llamadas_programadas DESC
            """)
            
            stats = cursor.fetchall()
            print("Distribución por estado de lead:")
            total = 0
            for stat in stats:
                count = stat['llamadas_programadas']
                total += count
                print(f"  {stat['estado_lead']}: {count} llamadas")
            
            print(f"  TOTAL: {total} llamadas programadas")
            print()
            
            # Detalles de llamadas para leads cerrados
            cursor.execute("""
                SELECT 
                    cs.id as schedule_id,
                    cs.lead_id,
                    cs.scheduled_at,
                    l.nombre,
                    l.apellidos,
                    l.closure_reason,
                    l.updated_at as lead_updated
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                    AND l.lead_status = 'closed'
                ORDER BY cs.scheduled_at
            """)
            
            closed_calls = cursor.fetchall()
            if closed_calls:
                print(f"LLAMADAS PROGRAMADAS PARA LEADS CERRADOS ({len(closed_calls)}):")
                for call in closed_calls:
                    print(f"  Schedule {call['schedule_id']} - Lead {call['lead_id']}")
                    print(f"    {call['nombre']} {call['apellidos']}")
                    print(f"    Programado: {call['scheduled_at']}")
                    print(f"    Cerrado: {call['closure_reason']} ({call['lead_updated']})")
                    print()
            else:
                print("No hay llamadas programadas para leads cerrados")
                
    except Exception as e:
        print(f"Error consultando estado: {e}")
    finally:
        conn.close()

def probar_cancelacion_por_llamada():
    """Prueba la cancelación de llamadas cuando se realiza una llamada no programada"""
    print("\nPROBANDO CANCELACIÓN POR LLAMADA NO PROGRAMADA")
    print("=" * 50)
    
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Buscar un lead con llamadas programadas
            cursor.execute("""
                SELECT 
                    cs.lead_id,
                    l.nombre,
                    l.apellidos,
                    COUNT(cs.id) as llamadas_programadas
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                    AND (l.lead_status IS NULL OR l.lead_status = 'open')
                GROUP BY cs.lead_id, l.nombre, l.apellidos
                LIMIT 1
            """)
            
            lead_with_calls = cursor.fetchone()
            
            if lead_with_calls:
                lead_id = lead_with_calls['lead_id']
                print(f"Lead seleccionado: {lead_id} - {lead_with_calls['nombre']} {lead_with_calls['apellidos']}")
                print(f"Llamadas programadas: {lead_with_calls['llamadas_programadas']}")
                
                # Simular llamada no programada
                print(f"\nSimulando llamada no programada para lead {lead_id}...")
                cancelled = cancel_scheduled_calls_for_lead(lead_id, "Prueba de cancelación")
                
                if cancelled > 0:
                    print(f"[OK] Canceladas {cancelled} llamadas programadas")
                else:
                    print("[INFO] No había llamadas para cancelar")
                    
            else:
                print("No hay leads con llamadas programadas para probar")
                
    except Exception as e:
        print(f"Error en prueba: {e}")
    finally:
        conn.close()

def ejecutar_limpieza_completa():
    """Ejecuta la limpieza completa de llamadas para leads cerrados"""
    print("\nEJECUTANDO LIMPIEZA DE LEADS CERRADOS")
    print("=" * 40)
    
    # Ejecutar función de limpieza
    cancelled_count = cleanup_closed_leads_schedules()
    
    if cancelled_count > 0:
        print(f"[EXITO] Limpieza completada: {cancelled_count} llamadas canceladas")
    else:
        print("[INFO] No había llamadas para limpiar")

def main():
    """Función principal"""
    print("LIMPIEZA DE LLAMADAS PROGRAMADAS - REGLAS DE NEGOCIO")
    print("=" * 55)
    
    # 1. Mostrar estado actual
    mostrar_estado_actual()
    
    # 2. Ejecutar limpieza de leads cerrados
    ejecutar_limpieza_completa()
    
    # 3. Probar cancelación por llamada no programada
    probar_cancelacion_por_llamada()
    
    # 4. Mostrar estado final
    print("\nESTADO DESPUÉS DE LIMPIEZA")
    print("=" * 30)
    mostrar_estado_actual()

if __name__ == "__main__":
    main()
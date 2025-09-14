#!/usr/bin/env python3
"""
Script para probar el sistema de llamadas programadas sin hacer llamadas reales
"""
import pymysql
from datetime import datetime, timedelta
from config import settings

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

def mostrar_estadisticas_call_schedule():
    """Muestra estadísticas de la tabla call_schedule"""
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            print("=== ESTADÍSTICAS CALL_SCHEDULE ===")
            
            # Total de registros por status
            cursor.execute("""
                SELECT status, COUNT(*) as total
                FROM call_schedule
                GROUP BY status
            """)
            results = cursor.fetchall()
            print("Distribución por status:")
            for row in results:
                print(f"  {row['status']}: {row['total']} registros")
            
            # Llamadas pendientes que deberían ejecutarse ahora
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                    AND cs.scheduled_at <= NOW()
                    AND (l.lead_status IS NULL OR l.lead_status = 'open')
            """)
            pendientes = cursor.fetchone()['total']
            print(f"Llamadas PENDIENTES para ejecutar AHORA: {pendientes}")
            
            # Próximas llamadas programadas
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                    AND cs.scheduled_at > NOW()
                    AND (l.lead_status IS NULL OR l.lead_status = 'open')
            """)
            futuras = cursor.fetchone()['total']
            print(f"Llamadas programadas para MÁS TARDE: {futuras}")
            
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
    finally:
        conn.close()

def mostrar_llamadas_pendientes(limit=10):
    """Muestra las próximas llamadas pendientes"""
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            print(f"\n=== PRÓXIMAS {limit} LLAMADAS PENDIENTES ===")
            cursor.execute("""
                SELECT 
                    cs.id as schedule_id,
                    cs.lead_id,
                    cs.scheduled_at,
                    cs.attempt_number,
                    cs.last_outcome,
                    l.nombre,
                    l.apellidos,
                    l.telefono,
                    l.call_attempts_count,
                    l.lead_status
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                    AND cs.scheduled_at <= NOW()
                    AND (l.lead_status IS NULL OR l.lead_status = 'open')
                    AND (l.manual_management IS NULL OR l.manual_management = FALSE)
                ORDER BY cs.scheduled_at ASC, cs.attempt_number ASC
                LIMIT %s
            """, (limit,))
            
            results = cursor.fetchall()
            if not results:
                print("  No hay llamadas pendientes para ejecutar ahora")
                return
            
            for i, call in enumerate(results, 1):
                tiempo_retraso = datetime.now() - call['scheduled_at']
                retraso_min = int(tiempo_retraso.total_seconds() / 60)
                
                print(f"{i:2d}. Lead {call['lead_id']} - {call['telefono']}")
                print(f"     Nombre: {call['nombre']} {call['apellidos']}")
                print(f"     Programado: {call['scheduled_at']} (retraso: {retraso_min}min)")
                print(f"     Intento: {call['attempt_number']} | Último resultado: {call['last_outcome']}")
                print(f"     Status: {call['lead_status']} | Intentos totales: {call['call_attempts_count']}")
                print()
            
    except Exception as e:
        print(f"Error obteniendo llamadas pendientes: {e}")
    finally:
        conn.close()

def simular_proceso_llamada_exitosa(schedule_id, lead_id):
    """Simula una llamada exitosa"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            print(f"[SIMULACION] Llamada exitosa para lead {lead_id}")
            
            # Solo marcar el schedule como completado
            cursor.execute("""
                UPDATE call_schedule
                SET status = 'completed',
                    updated_at = NOW()
                WHERE id = %s
            """, (schedule_id,))
            
            # Actualizar lead con valores válidos del enum
            cursor.execute("""
                UPDATE leads
                SET call_status = 'completed',
                    last_call_attempt = NOW(),
                    selected_for_calling = FALSE,
                    status_level_1 = 'Interesado'
                WHERE id = %s
            """, (lead_id,))
            
            conn.commit()
            print(f"    -> Lead {lead_id} marcado como contactado exitosamente")
            return True
            
    except Exception as e:
        print(f"Error simulando llamada exitosa: {e}")
        return False
    finally:
        conn.close()

def simular_proceso_llamada_fallida(schedule_id, lead_id):
    """Simula una llamada fallida sin reprogramar"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            print(f"[SIMULACION] Llamada fallida para lead {lead_id} (no_answer)")
            
            # Solo marcar el schedule como completado
            cursor.execute("""
                UPDATE call_schedule
                SET status = 'completed',
                    updated_at = NOW()
                WHERE id = %s
            """, (schedule_id,))
            
            # Actualizar lead con valores válidos del enum
            cursor.execute("""
                UPDATE leads
                SET call_status = 'no_answer',
                    last_call_attempt = NOW(),
                    selected_for_calling = FALSE,
                    call_attempts_count = COALESCE(call_attempts_count, 0) + 1
                WHERE id = %s
            """, (lead_id,))
            
            conn.commit()
            print(f"    -> Lead {lead_id} marcado como llamada fallida")
            return True
            
    except Exception as e:
        print(f"Error simulando llamada fallida: {e}")
        return False
    finally:
        conn.close()

def probar_reprogramacion_automatica():
    """Prueba la reprogramación automática de llamadas fallidas"""
    print("\n=== PROBANDO REPROGRAMACIÓN AUTOMÁTICA ===")
    
    # Crear una llamada fallida y probar que se reprograma
    from reprogramar_llamadas_simple import simple_reschedule_failed_call
    
    # Buscar un lead abierto
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, apellidos, call_attempts_count
                FROM leads
                WHERE (lead_status IS NULL OR lead_status = 'open')
                    AND call_attempts_count < 3
                LIMIT 1
            """)
            
            lead = cursor.fetchone()
            if not lead:
                print("No hay leads disponibles para probar reprogramación")
                return
            
            lead_id = lead['id']
            print(f"Probando reprogramación con lead {lead_id} - {lead['nombre']} {lead['apellidos']}")
            print(f"Intentos actuales: {lead['call_attempts_count']}")
            
            # Simular llamada fallida y reprogramar
            resultado = simple_reschedule_failed_call(lead_id, 'no_answer')
            
            if resultado:
                print(f"[OK] Lead {lead_id} reprogramado exitosamente")
                
                # Verificar que se creó el schedule
                cursor.execute("""
                    SELECT id, scheduled_at, attempt_number, status
                    FROM call_schedule
                    WHERE lead_id = %s AND status = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (lead_id,))
                
                schedule = cursor.fetchone()
                if schedule:
                    print(f"  Programado para: {schedule['scheduled_at']}")
                    print(f"  Intento numero: {schedule['attempt_number']}")
                else:
                    print("  [AVISO] No se encontro programacion en call_schedule")
            else:
                print(f"[ERROR] Lead {lead_id} no fue reprogramado (probablemente cerrado)")
                
    except Exception as e:
        print(f"Error probando reprogramación: {e}")
    finally:
        conn.close()

def probar_sistema_completo():
    """Prueba completa del sistema de llamadas programadas"""
    print("PROBANDO SISTEMA DE LLAMADAS PROGRAMADAS")
    print("=" * 50)
    
    # 1. Mostrar estadísticas actuales
    mostrar_estadisticas_call_schedule()
    
    # 2. Mostrar llamadas pendientes
    mostrar_llamadas_pendientes(5)
    
    # 3. Simular procesamiento de algunas llamadas
    print("\n=== SIMULACIÓN DE PROCESAMIENTO ===")
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cs.id, cs.lead_id
                    FROM call_schedule cs
                    JOIN leads l ON cs.lead_id = l.id
                    WHERE cs.status = 'pending'
                        AND cs.scheduled_at <= NOW()
                        AND (l.lead_status IS NULL OR l.lead_status = 'open')
                    LIMIT 3
                """)
                
                llamadas = cursor.fetchall()
                for i, call in enumerate(llamadas):
                    if i >= 2:  # Solo procesar las primeras 2 para evitar conflictos
                        break
                    # Alternar entre éxito y fallo para la simulación
                    if i % 2 == 0:
                        simular_proceso_llamada_exitosa(call['id'], call['lead_id'])
                    else:
                        simular_proceso_llamada_fallida(call['id'], call['lead_id'])
                
        except Exception as e:
            print(f"Error en simulación: {e}")
        finally:
            conn.close()
    
    # 4. Probar reprogramación automática
    probar_reprogramacion_automatica()
    
    # 5. Mostrar estadísticas después de la simulación
    print("\n=== ESTADÍSTICAS DESPUÉS DE SIMULACIÓN ===")
    mostrar_estadisticas_call_schedule()

if __name__ == "__main__":
    probar_sistema_completo()
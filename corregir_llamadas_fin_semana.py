#!/usr/bin/env python3
"""
Script para corregir llamadas programadas en fin de semana
y moverlas al próximo día laborable
"""
import pymysql
from datetime import datetime, timedelta
from config import settings
from reprogramar_llamadas_simple import get_working_hours_config, calculate_next_working_datetime

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

def corregir_llamadas_fin_semana():
    """Corrige llamadas programadas en fin de semana"""
    print("CORRIGIENDO LLAMADAS PROGRAMADAS EN FIN DE SEMANA")
    print("=" * 50)
    
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Encontrar llamadas en fin de semana (sábado=7, domingo=1 en MySQL)
            cursor.execute("""
                SELECT 
                    cs.id,
                    cs.lead_id,
                    cs.scheduled_at,
                    cs.attempt_number,
                    DAYOFWEEK(cs.scheduled_at) as dia_semana,
                    l.nombre,
                    l.apellidos
                FROM call_schedule cs
                JOIN leads l ON cs.lead_id = l.id
                WHERE cs.status = 'pending'
                    AND (DAYOFWEEK(cs.scheduled_at) = 1 OR DAYOFWEEK(cs.scheduled_at) = 7)
                    AND (l.lead_status IS NULL OR l.lead_status = 'open')
                ORDER BY cs.scheduled_at
            """)
            
            weekend_calls = cursor.fetchall()
            
            if not weekend_calls:
                print("[OK] No hay llamadas programadas en fin de semana para corregir")
                return
            
            print(f"Encontradas {len(weekend_calls)} llamadas en fin de semana:")
            print()
            
            correcciones = []
            
            for call in weekend_calls:
                dia_name = 'Domingo' if call['dia_semana'] == 1 else 'Sábado'
                print(f"ID {call['id']} - {call['scheduled_at']} ({dia_name})")
                print(f"  Lead {call['lead_id']}: {call['nombre']} {call['apellidos']}")
                
                # Calcular nueva fecha laborable
                # Usar 0 horas de delay para mover al siguiente día laborable manteniendo la hora
                nueva_fecha = calculate_next_working_datetime(call['scheduled_at'], 0)
                
                print(f"  Nueva fecha: {nueva_fecha}")
                print()
                
                correcciones.append({
                    'id': call['id'],
                    'antigua': call['scheduled_at'],
                    'nueva': nueva_fecha
                })
            
            # Confirmar corrección
            print("Proceder con las correcciones? (y/N): ")
            respuesta = input().strip().lower()
            
            if respuesta == 'y':
                print("\nAplicando correcciones...")
                
                for correccion in correcciones:
                    cursor.execute("""
                        UPDATE call_schedule
                        SET scheduled_at = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (correccion['nueva'], correccion['id']))
                    
                    print(f"[OK] Schedule ID {correccion['id']}: {correccion['antigua']} -> {correccion['nueva']}")
                
                conn.commit()
                print(f"\n[EXITO] {len(correcciones)} llamadas corregidas exitosamente")
                
            else:
                print("Corrección cancelada")
    
    except Exception as e:
        print(f"Error corrigiendo llamadas: {e}")
    finally:
        conn.close()

def verificar_configuracion():
    """Verifica la configuración de días laborables"""
    print("\nVERIFICACIÓN DE CONFIGURACIÓN")
    print("=" * 30)
    
    config = get_working_hours_config()
    
    dias_nombres = {
        1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 
        4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'
    }
    
    print(f"Horario laboral: {config['working_hours_start']} - {config['working_hours_end']}")
    
    dias_lab = [dias_nombres[d] for d in config['working_days']]
    print(f"Días laborables: {', '.join(dias_lab)}")
    
    # Probar la función con diferentes días
    print("\nPRUEBAS DE CÁLCULO:")
    
    # Domingo a las 14:00
    domingo = datetime(2025, 9, 14, 14, 0)  # Hoy domingo
    resultado = calculate_next_working_datetime(domingo, 4)  # +4 horas
    print(f"Domingo 14:00 + 4h -> {resultado} ({resultado.strftime('%A')})")
    
    # Viernes tarde
    viernes = datetime(2025, 9, 13, 19, 0)  # Viernes 19:00
    resultado = calculate_next_working_datetime(viernes, 4)  # +4 horas
    print(f"Viernes 19:00 + 4h -> {resultado} ({resultado.strftime('%A')})")

if __name__ == "__main__":
    verificar_configuracion()
    print()
    corregir_llamadas_fin_semana()
#!/usr/bin/env python3
"""
Script para resetear los contadores de llamadas incorrectos del archivo Septiembre
Resetea call_attempts_count a valores reales basados en historial de pearl_calls
"""
import pymysql
from datetime import datetime
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

def reset_contadores_septiembre():
    """Resetea los contadores de llamadas del archivo Septiembre"""
    print("RESETEANDO CONTADORES DE LLAMADAS - ARCHIVO SEPTIEMBRE")
    print("=" * 54)
    
    conn = get_connection()
    if not conn:
        return
    
    try:
        with conn.cursor() as cursor:
            # Contar llamadas reales por lead del archivo Septiembre
            cursor.execute("""
                SELECT 
                    l.id as lead_id,
                    l.call_attempts_count as contador_incorrecto,
                    COUNT(pc.id) as llamadas_reales,
                    l.nombre,
                    l.apellidos
                FROM leads l
                LEFT JOIN pearl_calls pc ON l.id = pc.lead_id
                WHERE l.origen_archivo = 'Septiembre'
                GROUP BY l.id, l.call_attempts_count, l.nombre, l.apellidos
                ORDER BY l.id
            """)
            
            leads = cursor.fetchall()
            
            print(f"Procesando {len(leads)} leads del archivo Septiembre...")
            print()
            
            # Mostrar algunos ejemplos del problema
            print("EJEMPLOS DE CONTADORES INCORRECTOS:")
            ejemplos_mostrados = 0
            for lead in leads[:10]:
                if lead['contador_incorrecto'] and lead['contador_incorrecto'] > 100:
                    print(f"Lead {lead['lead_id']}: {lead['nombre']} {lead['apellidos']}")
                    print(f"  Contador incorrecto: {lead['contador_incorrecto']:,}")
                    print(f"  Llamadas reales: {lead['llamadas_reales']}")
                    print()
                    ejemplos_mostrados += 1
                
                if ejemplos_mostrados >= 5:
                    break
            
            # Confirmar acción
            print("ACCION A REALIZAR:")
            print("- Resetear call_attempts_count = número real de llamadas de Pearl AI")
            print("- Esto corregirá el sistema de máximo de intentos")
            print()
            
            respuesta = input("¿Proceder con el reset? (y/N): ")
            
            if respuesta.lower() == 'y':
                print("\nEjecutando reset...")
                
                # Resetear todos los contadores
                cursor.execute("""
                    UPDATE leads l
                    LEFT JOIN (
                        SELECT lead_id, COUNT(*) as real_count
                        FROM pearl_calls
                        GROUP BY lead_id
                    ) pc ON l.id = pc.lead_id
                    SET l.call_attempts_count = COALESCE(pc.real_count, 0)
                    WHERE l.origen_archivo = 'Septiembre'
                """)
                
                affected = cursor.rowcount
                conn.commit()
                
                print(f"✅ Reset completado: {affected} leads actualizados")
                
                # Verificar resultado
                cursor.execute("""
                    SELECT 
                        MIN(call_attempts_count) as minimo,
                        MAX(call_attempts_count) as maximo,
                        AVG(call_attempts_count) as promedio,
                        COUNT(CASE WHEN call_attempts_count > 20 THEN 1 END) as altos
                    FROM leads
                    WHERE origen_archivo = 'Septiembre'
                        AND call_attempts_count IS NOT NULL
                """)
                
                stats = cursor.fetchone()
                
                print("\nESTADISTICAS DESPUES DEL RESET:")
                print(f"  Rango: {stats['minimo']} - {stats['maximo']}")
                print(f"  Promedio: {stats['promedio']:.1f}")
                print(f"  Leads con >20 intentos: {stats['altos']}")
                
            else:
                print("Reset cancelado")
                
    except Exception as e:
        print(f"Error en reset: {e}")
        if conn:
            conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_contadores_septiembre()
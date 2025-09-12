#!/usr/bin/env python3
"""
Script para procesar manualmente las llamadas del lead 634307425
usando los datos ya obtenidos de Pearl AI
"""
import pymysql
from config import settings
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_db():
    """Conectar a la base de datos usando pymysql como el script que funciona"""
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
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

def procesar_cita_manual():
    """
    Procesa manualmente la información de cita para el lead 634307425
    usando los datos que ya obtuvimos de Pearl AI
    """
    print("PROCESANDO MANUALMENTE CITA PARA LEAD 634307425")
    print("="*60)
    
    # Datos extraídos de Pearl AI (llamada más reciente)
    lead_id = 2454
    fecha_deseada = "25-09-2025"  # DD-MM-YYYY
    hora_deseada = "17:00:00"     # HH:MM:SS
    status_resultado = "Cita Agendada"
    resultado_llamada = "Cita confirmada"
    
    print(f"Lead ID: {lead_id}")
    print(f"Fecha Pearl AI: {fecha_deseada} -> Convertir a MySQL: 2025-09-25")
    print(f"Hora Pearl AI: {hora_deseada}")
    print(f"Status: {status_resultado}")
    print(f"Resultado: {resultado_llamada}")
    
    connection = connect_to_db()
    if not connection:
        print("No se pudo conectar a la base de datos")
        return
    
    try:
        with connection.cursor() as cursor:
            # Convertir fecha DD-MM-YYYY a YYYY-MM-DD
            fecha_parts = fecha_deseada.split('-')
            mysql_date = f"{fecha_parts[2]}-{fecha_parts[1]}-{fecha_parts[0]}"
            
            print(f"\nEjecutando UPDATE para lead {lead_id}...")
            
            # Actualizar el lead con la información de cita Y CERRARLO
            sql = """
                UPDATE leads SET
                    cita = %s,
                    hora_cita = %s,
                    status_level_1 = %s,
                    call_status = 'completed',
                    lead_status = 'closed',
                    closure_reason = 'Cita agendada',
                    selected_for_calling = FALSE,
                    updated_at = NOW()
                WHERE id = %s
            """
            
            cursor.execute(sql, (mysql_date, hora_deseada, status_resultado, lead_id))
            
            if cursor.rowcount > 0:
                print(f"Actualizado {cursor.rowcount} registro(s)")
                connection.commit()
                print("Cambios guardados exitosamente!")
                
                # Verificar el resultado
                print("\nVerificando resultado...")
                cursor.execute("""
                    SELECT id, nombre, apellidos, telefono,
                           cita, hora_cita, status_level_1, resultado_llamada,
                           call_status, lead_status, closure_reason, selected_for_calling, updated_at
                    FROM leads 
                    WHERE id = %s
                """, (lead_id,))
                
                lead = cursor.fetchone()
                
                if lead:
                    print("\nRESULTADO FINAL:")
                    print(f"Nombre: {lead['nombre']} {lead['apellidos']}")
                    print(f"Telefono: {lead['telefono']}")
                    print(f"Cita: {lead['cita']}")
                    print(f"Hora cita: {lead['hora_cita']}")
                    print(f"Status Level 1: {lead['status_level_1']}")
                    print(f"Resultado llamada: {lead['resultado_llamada']}")
                    print(f"Call Status: {lead['call_status']}")
                    print(f"Lead Status: {lead['lead_status']}")
                    print(f"Closure Reason: {lead['closure_reason']}")
                    print(f"Selected for calling: {lead['selected_for_calling']}")
                    print(f"Actualizado: {lead['updated_at']}")
                    
                    # Verificar si todo está correcto
                    success = True
                    expected_date = "2025-09-25"
                    expected_time = "17:00:00"
                    
                    if str(lead['cita']) != expected_date:
                        print(f"ERROR: Fecha esperada {expected_date}, obtenida {lead['cita']}")
                        success = False
                    if str(lead['hora_cita']) != expected_time:
                        print(f"ERROR: Hora esperada {expected_time}, obtenida {lead['hora_cita']}")
                        success = False
                    if lead['status_level_1'] != status_resultado:
                        print(f"ERROR: Status esperado {status_resultado}, obtenido {lead['status_level_1']}")
                        success = False
                    if lead['lead_status'] != 'closed':
                        print(f"ERROR: Lead debería estar 'closed', pero está '{lead['lead_status']}'")
                        success = False
                    if lead['closure_reason'] != 'Cita agendada':
                        print(f"ERROR: Closure reason esperado 'Cita agendada', obtenido '{lead['closure_reason']}'")
                        success = False
                    if lead['selected_for_calling'] != 0:
                        print(f"ERROR: Selected for calling debería ser 0 (FALSE), pero es {lead['selected_for_calling']}")
                        success = False
                        
                    if success:
                        print("\n*** EXITO COMPLETO: El lead tiene la cita procesada Y está CERRADO correctamente! ***")
                        print("- El problema en la pantalla /leads está resuelto")
                        print("- El lead no será seleccionado para más llamadas")
                        print("- El estado es 'Cita Agendada' y 'closed'")
                    else:
                        print("\nAlgunos campos no se actualizaron correctamente.")
                        
            else:
                print("No se actualizó ningún registro. Verificar que el lead_id existe.")
                
    except Exception as e:
        print(f"Error procesando: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    procesar_cita_manual()
"""
Script para reprocesar todas las llamadas que tienen callData (collected_info) 
y enviarlas de nuevo a la API actualizar_resultado para detectar citas perdidas.
"""

import mysql.connector
import json
import requests
import time
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def extract_fields_from_call_data(call_data_json):
    """
    Extrae campos relevantes del callData JSON para enviar a la API
    """
    try:
        if isinstance(call_data_json, str):
            call_data = json.loads(call_data_json)
        elif isinstance(call_data_json, dict):
            call_data = call_data_json
        else:
            return {}
            
        # Extraer campos relevantes
        extracted = {}
        
        # Campos básicos
        if 'telefono' in call_data or 'phoneNumber' in call_data:
            extracted['telefono'] = call_data.get('telefono') or call_data.get('phoneNumber', '').replace('+34', '').replace(' ', '').replace('-', '')
            
        # Campos de cita
        if 'fechaDeseada' in call_data:
            extracted['fechaDeseada'] = call_data['fechaDeseada']
            
        if 'preferenciaMT' in call_data:
            extracted['preferenciaMT'] = call_data['preferenciaMT']
            
        if 'callResult' in call_data:
            extracted['callResult'] = call_data['callResult']
            
        # Otros campos útiles
        for field in ['firstName', 'lastName', 'codigoPostal', 'delegacion', 
                     'fechaNacimiento', 'sexo', 'agentName', 'interesado', 
                     'sr_sra', 'dias_tardes', 'conPack', 'nuevaCita']:
            if field in call_data:
                extracted[field] = call_data[field]
        
        return extracted
        
    except Exception as e:
        logger.error(f"Error extrayendo campos de callData: {e}")
        return {}

def send_to_api(data):
    """
    Envía datos a la API actualizar_resultado
    """
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    try:
        response = requests.post(api_url, json=data, timeout=30)
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response': response.text[:200] if response.text else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def reprocesar_calls_con_calldata():
    """
    Busca todas las llamadas con collected_info y las reprocesa
    """
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar llamadas de los últimos 30 días con collected_info no vacío
        logger.info("Buscando llamadas con callData de los últimos 30 días...")
        
        cursor.execute("""
            SELECT 
                pc.id,
                pc.call_id,
                pc.phone_number,
                pc.call_time,
                pc.collected_info,
                l.id as lead_id,
                l.nombre,
                l.apellidos,
                l.status_level_1,
                l.status_level_2
            FROM pearl_calls pc
            LEFT JOIN leads l ON CAST(REPLACE(REPLACE(pc.phone_number, '+34', ''), ' ', '') AS CHAR) = CAST(l.telefono AS CHAR)
            WHERE pc.collected_info IS NOT NULL 
            AND pc.collected_info != ''
            AND pc.collected_info != '{}'
            AND pc.call_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY pc.call_time DESC
        """)
        
        calls = cursor.fetchall()
        
        if not calls:
            logger.info("No se encontraron llamadas con callData")
            return
            
        logger.info(f"Encontradas {len(calls)} llamadas con callData para reprocesar")
        
        # Estadísticas
        processed = 0
        appointments_found = 0
        api_errors = 0
        
        for call in calls:
            try:
                # Extraer campos del callData
                call_data_fields = extract_fields_from_call_data(call['collected_info'])
                
                if not call_data_fields:
                    logger.debug(f"Sin campos útiles en call {call['call_id']}")
                    continue
                    
                # Verificar si tiene fechaDeseada o callResult relacionado con cita
                has_appointment_indicators = (
                    call_data_fields.get('fechaDeseada') or
                    call_data_fields.get('preferenciaMT') or
                    (call_data_fields.get('callResult', '').lower() in ['cita agendada', 'cita confirmada'])
                )
                
                if has_appointment_indicators:
                    logger.info(f"🎯 Reprocesando call {call['call_id']} - Lead {call['lead_id']} ({call.get('nombre', 'N/A')} {call.get('apellidos', 'N/A')})")
                    logger.info(f"   Campos: {call_data_fields}")
                    
                    # Enviar a API
                    result = send_to_api(call_data_fields)
                    
                    if result['success']:
                        appointments_found += 1
                        logger.info(f"   ✅ Enviado exitosamente")
                    else:
                        api_errors += 1
                        logger.warning(f"   ❌ Error API: {result.get('error', result.get('status_code'))}")
                
                processed += 1
                
                # Pausa para no saturar la API
                time.sleep(0.1)
                
                # Progreso cada 50 llamadas
                if processed % 50 == 0:
                    logger.info(f"Progreso: {processed}/{len(calls)} procesadas")
                    
            except Exception as e:
                logger.error(f"Error procesando call {call.get('call_id', 'N/A')}: {e}")
        
        # Resumen final
        logger.info(f"""
╔══════════════════════════════════════════════════╗
║              REPROCESO COMPLETADO                ║
╠══════════════════════════════════════════════════╣
║ Total llamadas revisadas:           {len(calls):4d}    ║
║ Llamadas procesadas:                {processed:4d}    ║
║ Citas potenciales encontradas:      {appointments_found:4d}    ║
║ Errores de API:                     {api_errors:4d}    ║
╚══════════════════════════════════════════════════╝
        """)
        
        if appointments_found > 0:
            logger.info(f"""
📊 VERIFICACIÓN RECOMENDADA:
- Revisar leads que ahora deberían tener status_level_1 = 'Cita Agendada'
- Ejecutar: python obtener_leads_cita.py para ver los resultados
            """)
            
    except Exception as e:
        logger.error(f"Error en reproceso: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("="*60)
    print("REPROCESO DE LLAMADAS CON CALLDATA")
    print("="*60)
    print("Este script:")
    print("1. Busca llamadas con callData de los últimos 30 días")
    print("2. Identifica las que tienen fechaDeseada, preferenciaMT o callResult de cita")
    print("3. Las reenvía a la API actualizar_resultado para detectar citas perdidas")
    print()
    
    input("Presiona ENTER para continuar...")
    
    reprocesar_calls_con_calldata()
    
    print("="*60)
    print("REPROCESO COMPLETADO")
    print("="*60)
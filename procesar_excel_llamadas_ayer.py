"""
Script para procesar el Excel con llamadas de ayer y reprocesar 
los leads con interés que no fueron marcados correctamente.
"""

import pandas as pd
import json
import requests
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_appointment_data_from_json(collected_info_str):
    """
    Extrae datos de cita del JSON en collectedInfo
    """
    try:
        if not collected_info_str or pd.isna(collected_info_str):
            return None
            
        # Parsear JSON
        if isinstance(collected_info_str, str):
            data = json.loads(collected_info_str)
        else:
            data = collected_info_str
            
        # Buscar indicadores de cita
        appointment_indicators = {}
        
        # Campos directos de cita
        if data.get('fechaDeseada'):
            appointment_indicators['fechaDeseada'] = data['fechaDeseada']
            
        if data.get('preferenciaMT'):
            appointment_indicators['preferenciaMT'] = data['preferenciaMT']
            
        if data.get('callResult'):
            call_result = str(data['callResult']).lower()
            if any(keyword in call_result for keyword in ['cita', 'agendada', 'confirmada']):
                appointment_indicators['callResult'] = data['callResult']
        
        # Buscar otros campos que indiquen interés
        if data.get('interesado'):
            interesado = str(data['interesado']).lower()
            if 'interesado' in interesado:
                appointment_indicators['interesado'] = data['interesado']
        
        # Campos adicionales útiles
        for field in ['telefono', 'phoneNumber', 'firstName', 'lastName', 
                     'codigoPostal', 'delegacion', 'fechaNacimiento', 'sexo', 
                     'agentName', 'sr_sra', 'conPack', 'nuevaCita']:
            if field in data:
                appointment_indicators[field] = data[field]
        
        # Solo devolver si tiene indicadores de cita o interés
        if (appointment_indicators.get('fechaDeseada') or 
            appointment_indicators.get('preferenciaMT') or 
            appointment_indicators.get('callResult') or
            appointment_indicators.get('interesado')):
            return appointment_indicators
            
        return None
        
    except Exception as e:
        logger.debug(f"Error parseando JSON: {e}")
        return None

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
            'response_text': response.text[:200] if response.text else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def procesar_excel_llamadas():
    """
    Procesa el Excel con llamadas de ayer
    """
    file_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\NLPearlCalls09_10_2025 00_00_00__09_10_2025 23_59_59.xlsx"
    
    try:
        # Leer Excel
        logger.info(f"Leyendo Excel: {file_path}")
        df = pd.read_excel(file_path)
        
        logger.info(f"Encontradas {len(df)} filas en el Excel")
        logger.info(f"Columnas disponibles: {list(df.columns)}")
        
        # Verificar que existe la columna collectedInfo
        collected_info_col = None
        for col in df.columns:
            if 'collected' in col.lower() or 'info' in col.lower():
                collected_info_col = col
                break
        
        if not collected_info_col:
            logger.error("No se encontró la columna 'collectedInfo' en el Excel")
            return
        
        logger.info(f"Usando columna: {collected_info_col}")
        
        # Procesar cada fila
        appointments_found = 0
        api_calls_made = 0
        api_successes = 0
        errors = 0
        
        results_log = []
        
        for idx, row in df.iterrows():
            try:
                # Extraer datos de cita del JSON
                appointment_data = extract_appointment_data_from_json(row[collected_info_col])
                
                if appointment_data:
                    # Obtener teléfono
                    telefono = (appointment_data.get('telefono') or 
                              appointment_data.get('phoneNumber', ''))
                    
                    if telefono:
                        telefono = str(telefono).replace('+34', '').replace(' ', '').replace('-', '')
                        appointment_data['telefono'] = telefono
                        
                    logger.info(f"🎯 Fila {idx+1}: Cita encontrada para {appointment_data.get('firstName', 'N/A')} {appointment_data.get('lastName', 'N/A')}")
                    logger.info(f"   Tel: {telefono}")
                    logger.info(f"   Datos: {appointment_data}")
                    
                    # Enviar a API
                    if telefono:
                        api_result = send_to_api(appointment_data)
                        api_calls_made += 1
                        
                        if api_result['success']:
                            api_successes += 1
                            logger.info(f"   ✅ API exitosa")
                            
                            results_log.append({
                                'fila': idx+1,
                                'telefono': telefono,
                                'nombre': f"{appointment_data.get('firstName', '')} {appointment_data.get('lastName', '')}",
                                'datos_cita': str(appointment_data),
                                'api_status': 'SUCCESS',
                                'api_response': api_result.get('response_text', '')
                            })
                        else:
                            errors += 1
                            logger.warning(f"   ❌ Error API: {api_result.get('error', api_result.get('status_code'))}")
                            
                            results_log.append({
                                'fila': idx+1,
                                'telefono': telefono,
                                'nombre': f"{appointment_data.get('firstName', '')} {appointment_data.get('lastName', '')}",
                                'datos_cita': str(appointment_data),
                                'api_status': 'ERROR',
                                'api_response': api_result.get('error', api_result.get('status_code'))
                            })
                    else:
                        logger.warning(f"   ⚠️ Sin teléfono válido")
                        errors += 1
                    
                    appointments_found += 1
                    
                    # Pausa para no saturar la API
                    time.sleep(0.5)
                
                # Progreso cada 100 filas
                if (idx + 1) % 100 == 0:
                    logger.info(f"Progreso: {idx+1}/{len(df)} filas procesadas")
                    
            except Exception as e:
                logger.error(f"Error procesando fila {idx+1}: {e}")
                errors += 1
        
        # Resumen final
        logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║              PROCESAMIENTO EXCEL COMPLETADO             ║
╠══════════════════════════════════════════════════════════╣
║ Total filas en Excel:                          {len(df):4d}    ║
║ Citas/interés encontrados:                     {appointments_found:4d}    ║
║ Llamadas API realizadas:                       {api_calls_made:4d}    ║
║ API exitosas:                                  {api_successes:4d}    ║
║ Errores:                                       {errors:4d}    ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        # Guardar log de resultados
        if results_log:
            results_df = pd.DataFrame(results_log)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"procesamiento_excel_resultados_{timestamp}.xlsx"
            results_df.to_excel(results_file, index=False)
            logger.info(f"📊 Resultados guardados en: {results_file}")
            
    except Exception as e:
        logger.error(f"Error procesando Excel: {e}")

if __name__ == "__main__":
    print("="*70)
    print("PROCESAMIENTO DE EXCEL CON LLAMADAS DE AYER")
    print("="*70)
    print("Este script:")
    print("1. Lee el Excel con las llamadas del 09/10/2025")
    print("2. Extrae datos de cita/interés del JSON en collectedInfo")
    print("3. Envía los datos a la API actualizar_resultado")
    print("4. Actualiza los leads con citas perdidas")
    print()
    
    procesar_excel_llamadas()
    
    print("="*70)
    print("PROCESAMIENTO COMPLETADO")
    print("="*70)
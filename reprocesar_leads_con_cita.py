"""
Script para reprocesar todos los leads que tienen 'Cita Agendada' 
aplicando la lógica corregida de conPack desde el Excel original
"""

import pandas as pd
import json
import requests
import time
import mysql.connector
from datetime import datetime
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

def get_leads_with_cita():
    """
    Obtiene todos los leads que tienen 'Cita Agendada'
    """
    conn = get_railway_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, status_level_1, status_level_2, updated_at
            FROM leads 
            WHERE status_level_1 = 'Cita Agendada'
            ORDER BY updated_at DESC
        """)
        
        leads = cursor.fetchall()
        return leads
        
    except Exception as e:
        logger.error(f"Error obteniendo leads con cita: {e}")
        return []
    finally:
        if conn:
            conn.close()

def find_lead_data_in_excel(telefono, df):
    """
    Busca los datos originales del lead en el Excel
    """
    try:
        # Convertir columna 'To' a string para evitar errores
        df['To'] = df['To'].astype(str)
        
        # Buscar por teléfono en la columna 'To' - los teléfonos aparecen con prefijo 34 sin +
        # Ejemplo: 34613750493 en lugar de +34613750493
        patterns = [
            f"34{telefono}",     # Formato exacto del Excel
            f".*34{telefono}.*", # Prefijo España con contexto
            f".*{telefono}.*"    # Sin prefijo
        ]
        
        matching_rows = None
        for pattern in patterns:
            matching_rows = df[df['To'].str.contains(pattern, na=False, regex=True)]
            if not matching_rows.empty:
                logger.debug(f"Encontrado {telefono} con patrón: {pattern}")
                break
        
        if not matching_rows.empty:
            # Tomar la primera coincidencia
            row = matching_rows.iloc[0]
            
            # Extraer CollectedInfo
            collected_info = row.get('CollectedInfo', '{}')
            if pd.isna(collected_info) or collected_info == '':
                return None
                
            # Parsear JSON
            try:
                data = json.loads(collected_info)
                return data
            except json.JSONDecodeError:
                return None
        
        return None
        
    except Exception as e:
        logger.debug(f"Error buscando {telefono} en Excel: {e}")
        return None

def send_to_api(data):
    """
    Envía datos a la API actualizar_resultado
    """
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    try:
        response = requests.post(api_url, json=data, timeout=45)
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

def reprocesar_leads_con_cita():
    """
    Reprocesa todos los leads que tienen 'Cita Agendada'
    """
    # Cargar Excel
    excel_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\NLPearlCalls09_10_2025 00_00_00__09_10_2025 23_59_59.xlsx"
    
    try:
        logger.info("Cargando Excel con datos originales...")
        df = pd.read_excel(excel_path)
        logger.info(f"Excel cargado: {len(df)} filas")
        
        # Obtener leads con cita
        logger.info("Obteniendo leads con 'Cita Agendada'...")
        leads_con_cita = get_leads_with_cita()
        
        if not leads_con_cita:
            logger.info("No se encontraron leads con 'Cita Agendada'")
            return
            
        logger.info(f"Encontrados {len(leads_con_cita)} leads con 'Cita Agendada' para reprocesar")
        
        # Procesar cada lead
        processed = 0
        updated = 0
        errors = 0
        results = []
        
        for lead in leads_con_cita:
            try:
                telefono = lead['telefono']
                nombre_completo = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}"
                current_status_l2 = lead['status_level_2']  # Definir antes del if
                
                logger.info(f"Procesando Lead {lead['id']}: {nombre_completo} ({telefono})")
                logger.info(f"  Status actual: {current_status_l2}")
                
                # Buscar datos originales en Excel
                excel_data = find_lead_data_in_excel(telefono, df)
                
                if excel_data:
                    # Preparar datos para API
                    api_data = {
                        'telefono': telefono
                    }
                    
                    # Incluir campos relevantes
                    for field in ['firstName', 'lastName', 'fechaDeseada', 'preferenciaMT', 
                                 'callResult', 'interesado', 'conPack', 'phoneNumber',
                                 'codigoPostal', 'delegacion', 'fechaNacimiento', 'sexo',
                                 'agentName', 'sr_sra', 'nuevaCita']:
                        if field in excel_data:
                            api_data[field] = excel_data[field]
                    
                    logger.info(f"  Datos encontrados en Excel: {api_data}")
                    
                    # Determinar si debería ser Con Pack o Sin Pack
                    con_pack_original = excel_data.get('conPack') is True
                    expected_status = 'Con Pack' if con_pack_original else 'Sin Pack'
                    
                    logger.info(f"  Actual: {current_status_l2} | Esperado: {expected_status}")
                    
                    if current_status_l2 != expected_status:
                        # Necesita actualización
                        logger.info(f"  🔄 Reprocesando para corregir status...")
                        
                        result = send_to_api(api_data)
                        
                        if result['success']:
                            updated += 1
                            logger.info(f"  ✅ Actualizado exitosamente")
                            
                            results.append({
                                'lead_id': lead['id'],
                                'telefono': telefono,
                                'nombre': nombre_completo,
                                'status_anterior': current_status_l2,
                                'status_esperado': expected_status,
                                'resultado': 'SUCCESS'
                            })
                        else:
                            errors += 1
                            logger.warning(f"  ❌ Error API: {result.get('error', result.get('status_code'))}")
                            
                            results.append({
                                'lead_id': lead['id'],
                                'telefono': telefono,
                                'nombre': nombre_completo,
                                'status_anterior': current_status_l2,
                                'status_esperado': expected_status,
                                'resultado': f"ERROR: {result.get('error', result.get('status_code'))}"
                            })
                    else:
                        logger.info(f"  ✓ Ya está correcto")
                        results.append({
                            'lead_id': lead['id'],
                            'telefono': telefono,
                            'nombre': nombre_completo,
                            'status_anterior': current_status_l2,
                            'status_esperado': expected_status,
                            'resultado': 'ALREADY_CORRECT'
                        })
                        
                else:
                    logger.warning(f"  ⚠️ No encontrado en Excel")
                    results.append({
                        'lead_id': lead['id'],
                        'telefono': telefono,
                        'nombre': nombre_completo,
                        'status_anterior': current_status_l2,
                        'status_esperado': 'UNKNOWN',
                        'resultado': 'NOT_FOUND_IN_EXCEL'
                    })
                
                processed += 1
                time.sleep(1)  # Pausa entre llamadas
                
            except Exception as e:
                logger.error(f"Error procesando lead {lead['id']}: {e}")
                errors += 1
        
        # Resumen final
        logger.info(f"""
╔══════════════════════════════════════════════════╗
║           REPROCESO DE LEADS CON CITA           ║
╠══════════════════════════════════════════════════╣
║ Leads con cita encontrados:            {len(leads_con_cita):4d}    ║
║ Leads procesados:                      {processed:4d}    ║
║ Leads actualizados:                    {updated:4d}    ║
║ Errores:                               {errors:4d}    ║
╚══════════════════════════════════════════════════╝
        """)
        
        # Guardar resultados
        if results:
            results_df = pd.DataFrame(results)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"reproceso_citas_conpack_{timestamp}.xlsx"
            results_df.to_excel(results_file, index=False)
            logger.info(f"📊 Resultados guardados en: {results_file}")
            
    except Exception as e:
        logger.error(f"Error en reproceso: {e}")

if __name__ == "__main__":
    print("="*60)
    print("REPROCESO DE LEADS CON CITA (CORRECCIÓN CONPACK)")
    print("="*60)
    print("Este script:")
    print("1. Obtiene todos los leads con 'Cita Agendada'")
    print("2. Busca sus datos originales en el Excel")
    print("3. Verifica si conPack=true en el JSON original")
    print("4. Corrige el status_level_2 (Sin Pack vs Con Pack)")
    print()
    
    reprocesar_leads_con_cita()
    
    print("="*60)
    print("REPROCESO COMPLETADO")
    print("="*60)
#!/usr/bin/env python3
"""
Script para cargar el archivo Excel de Septiembre a Railway
"""

import pandas as pd
import mysql.connector
import logging
from urllib.parse import urlparse
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ruta del archivo Excel
ARCHIVO_EXCEL = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\01NP Dental_VoiceBot_20250902_TeYame.xlsx"
NOMBRE_ARCHIVO = "Septiembre"

def get_railway_connection():
    """Obtiene conexión a Railway usando MYSQL_URL"""
    mysql_url = os.getenv('MYSQL_URL')
    if not mysql_url:
        raise Exception("MYSQL_URL no está configurada")
    
    url = urlparse(mysql_url)
    config = {
        'host': url.hostname,
        'port': url.port or 3306,
        'user': url.username,
        'password': url.password,
        'database': url.path[1:]
    }
    
    logger.info(f"Conectando a Railway: {config['host']}:{config['port']} DB:{config['database']}")
    return mysql.connector.connect(**config)

def leer_archivo_excel():
    """Lee el archivo Excel y lo procesa"""
    logger.info(f"Leyendo archivo Excel: {ARCHIVO_EXCEL}")
    
    if not os.path.exists(ARCHIVO_EXCEL):
        raise FileNotFoundError(f"No se encontró el archivo: {ARCHIVO_EXCEL}")
    
    # Leer Excel
    df = pd.read_excel(ARCHIVO_EXCEL)
    logger.info(f"Archivo leído: {len(df)} registros, {len(df.columns)} columnas")
    
    # Mostrar información del archivo
    logger.info(f"Columnas disponibles: {list(df.columns)}")
    
    return df

def procesar_datos(df):
    """Procesa y limpia los datos del DataFrame"""
    logger.info("Procesando datos...")
    
    # Crear mapeo de columnas (ajustar según la estructura real del Excel)
    columnas_mapeo = {
        'nombre': ['nombre', 'Nombre', 'NOMBRE'],
        'apellidos': ['apellidos', 'Apellidos', 'APELLIDOS'],
        'telefono': ['telefono', 'Telefono', 'TELEFONO', 'teléfono', 'TELEFONO1'],
        'telefono2': ['telefono2', 'Telefono2', 'TELEFONO2', 'teléfono2'],
        'email': ['email', 'Email', 'EMAIL', 'correo'],
        'nif': ['nif', 'NIF', 'dni', 'DNI'],
        'fecha_nacimiento': ['fecha_nacimiento', 'Fecha_Nacimiento', 'FECHA_NACIMIENTO'],
        'sexo': ['sexo', 'Sexo', 'SEXO'],
        'poliza': ['poliza', 'Poliza', 'POLIZA', 'póliza'],
        'segmento': ['segmento', 'Segmento', 'SEGMENTO'],
        'certificado': ['certificado', 'Certificado', 'CERTIFICADO'],
        'delegacion': ['delegacion', 'Delegacion', 'DELEGACION', 'delegación'],
        'clinica_id': ['clinica_id', 'Clinica_ID', 'CLINICA_ID'],
        'nombre_clinica': ['nombre_clinica', 'Nombre_Clinica', 'NOMBRE_CLINICA'],
        'direccion_clinica': ['direccion_clinica', 'Direccion_Clinica', 'DIRECCION_CLINICA'],
        'codigo_postal': ['codigo_postal', 'Codigo_Postal', 'CODIGO_POSTAL', 'cp', 'CP'],
        'ciudad': ['ciudad', 'Ciudad', 'CIUDAD'],
        'area_id': ['area_id', 'Area_ID', 'AREA_ID']
    }
    
    # Crear DataFrame procesado
    df_procesado = pd.DataFrame()
    
    for campo_bd, posibles_nombres in columnas_mapeo.items():
        for nombre in posibles_nombres:
            if nombre in df.columns:
                df_procesado[campo_bd] = df[nombre]
                logger.info(f"Mapeado: {nombre} -> {campo_bd}")
                break
        
        # Si no se encuentra, crear columna vacía
        if campo_bd not in df_procesado.columns:
            df_procesado[campo_bd] = None
            logger.warning(f"Campo {campo_bd} no encontrado, usando NULL")
    
    # Añadir campos adicionales
    df_procesado['origen_archivo'] = NOMBRE_ARCHIVO
    df_procesado['match_source'] = 'Excel_Import'
    df_procesado['match_confidence'] = 100
    df_procesado['call_status'] = None
    df_procesado['call_priority'] = 3
    df_procesado['selected_for_calling'] = False
    df_procesado['call_attempts_count'] = 0
    df_procesado['lead_status'] = 'open'
    df_procesado['reserva_automatica'] = False
    df_procesado['preferencia_horario'] = 'mañana'
    df_procesado['manual_management'] = False
    df_procesado['conPack'] = False
    
    # Limpiar datos
    df_procesado = df_procesado.fillna('')  # Reemplazar NaN con string vacío
    
    logger.info(f"Datos procesados: {len(df_procesado)} registros")
    
    return df_procesado

def registrar_archivo_origen(cursor, total_registros):
    """Registra el archivo en la tabla archivos_origen"""
    logger.info("Registrando archivo en archivos_origen...")
    
    insert_archivo_sql = """
    INSERT INTO archivos_origen (nombre_archivo, descripcion, fecha_creacion, total_registros, usuario_creacion, activo)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    total_registros = VALUES(total_registros),
    fecha_creacion = VALUES(fecha_creacion)
    """
    
    valores_archivo = (
        NOMBRE_ARCHIVO,
        f"Archivo Excel de Septiembre - Dental VoiceBot 02/09/2025",
        datetime.now(),
        total_registros,
        "Sistema",
        True
    )
    
    cursor.execute(insert_archivo_sql, valores_archivo)
    logger.info(f"Archivo '{NOMBRE_ARCHIVO}' registrado con {total_registros} registros")

def insertar_leads(cursor, df_procesado):
    """Inserta los leads en la base de datos"""
    logger.info("Insertando leads en Railway...")
    
    # SQL de inserción
    insert_lead_sql = """
    INSERT INTO leads (
        nombre, apellidos, telefono, telefono2, email, nif, fecha_nacimiento, sexo,
        poliza, segmento, certificado, delegacion, clinica_id, nombre_clinica, 
        direccion_clinica, codigo_postal, ciudad, area_id, origen_archivo,
        match_source, match_confidence, call_status, call_priority, selected_for_calling,
        call_attempts_count, lead_status, reserva_automatica, preferencia_horario,
        manual_management, conPack
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """
    
    registros_insertados = 0
    registros_error = 0
    
    for index, row in df_procesado.iterrows():
        try:
            # Convertir fecha_nacimiento si existe
            fecha_nacimiento = None
            if row['fecha_nacimiento'] and str(row['fecha_nacimiento']).strip():
                try:
                    if isinstance(row['fecha_nacimiento'], str):
                        fecha_nacimiento = pd.to_datetime(row['fecha_nacimiento']).date()
                    else:
                        fecha_nacimiento = row['fecha_nacimiento']
                except:
                    fecha_nacimiento = None
            
            valores = (
                str(row['nombre'])[:100] if row['nombre'] else None,
                str(row['apellidos'])[:150] if row['apellidos'] else None,
                str(row['telefono'])[:20] if row['telefono'] else None,
                str(row['telefono2'])[:20] if row['telefono2'] else None,
                str(row['email'])[:255] if row['email'] else None,
                str(row['nif'])[:20] if row['nif'] else None,
                fecha_nacimiento,
                str(row['sexo'])[:10] if row['sexo'] else None,
                str(row['poliza'])[:50] if row['poliza'] else None,
                str(row['segmento'])[:100] if row['segmento'] else None,
                str(row['certificado'])[:100] if row['certificado'] else None,
                str(row['delegacion'])[:100] if row['delegacion'] else None,
                str(row['clinica_id'])[:50] if row['clinica_id'] else None,
                str(row['nombre_clinica'])[:255] if row['nombre_clinica'] else None,
                str(row['direccion_clinica'])[:255] if row['direccion_clinica'] else None,
                str(row['codigo_postal'])[:10] if row['codigo_postal'] else None,
                str(row['ciudad'])[:100] if row['ciudad'] else None,
                str(row['area_id'])[:100] if row['area_id'] else None,
                str(row['origen_archivo'])[:255],
                str(row['match_source'])[:50],
                int(row['match_confidence']),
                str(row['call_status']),
                int(row['call_priority']),
                bool(row['selected_for_calling']),
                int(row['call_attempts_count']),
                str(row['lead_status']),
                bool(row['reserva_automatica']),
                str(row['preferencia_horario']),
                bool(row['manual_management']),
                bool(row['conPack'])
            )
            
            cursor.execute(insert_lead_sql, valores)
            registros_insertados += 1
            
            if registros_insertados % 100 == 0:
                logger.info(f"Insertados {registros_insertados} registros...")
            
        except Exception as e:
            registros_error += 1
            logger.error(f"Error insertando registro {index}: {e}")
            continue
    
    logger.info(f"Inserción completada: {registros_insertados} exitosos, {registros_error} errores")
    return registros_insertados

def cargar_archivo_railway():
    """Función principal para cargar el archivo a Railway"""
    connection = None
    try:
        # 1. Leer archivo Excel
        df = leer_archivo_excel()
        
        # 2. Procesar datos
        df_procesado = procesar_datos(df)
        
        # 3. Conectar a Railway
        connection = get_railway_connection()
        cursor = connection.cursor()
        
        # 4. Registrar archivo origen
        registrar_archivo_origen(cursor, len(df_procesado))
        
        # 5. Insertar leads
        registros_insertados = insertar_leads(cursor, df_procesado)
        
        # 6. Confirmar transacción
        connection.commit()
        
        logger.info(f"✅ CARGA COMPLETADA EXITOSAMENTE")
        logger.info(f"Archivo: {NOMBRE_ARCHIVO}")
        logger.info(f"Registros insertados: {registros_insertados}")
        
        return registros_insertados
        
    except Exception as e:
        logger.error(f"❌ Error en la carga: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    try:
        registros = cargar_archivo_railway()
        print(f"\n🎉 ¡Archivo '{NOMBRE_ARCHIVO}' cargado exitosamente en Railway!")
        print(f"Total de registros insertados: {registros}")
    except Exception as e:
        print(f"\n💥 Error en la carga: {e}")
        exit(1)
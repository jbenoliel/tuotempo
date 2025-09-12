"""
Script para descargar grabaciones de llamadas de Pearl AI a partir de un archivo Excel.

El script pide al usuario la ruta de un archivo Excel y el nombre de la columna
que contiene los Call IDs. Luego, itera sobre cada ID, descarga la grabación
correspondiente y la guarda en una carpeta 'grabaciones_descargadas'.
"""

import os
import pandas as pd
import logging
import json
from datetime import datetime
from pearl_caller import get_pearl_client, PearlAPIError
from dotenv import load_dotenv
from db import get_connection
import mysql.connector
import re

# --- Configuración de Logging ---
log_directory = "logs"
os.makedirs(log_directory, exist_ok=True)
log_filename = os.path.join(log_directory, f"descarga_grabaciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Obtenemos el logger raíz y lo configuramos
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Limpiamos handlers existentes para evitar duplicados
if logger.hasHandlers():
    logger.handlers.clear()

# Creamos el formateador
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Creamos y añadimos el handler para el archivo con codificación UTF-8
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Creamos y añadimos el handler para la consola
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)



def _buscar_info_lead(db_cursor, phone: str, name: str) -> dict:
    """Busca información de un lead en la BD por teléfono o nombre."""
    lead_data = {}
    # Campos a recuperar de la tabla leads
    campos_lead = [
        'fecha_nacimiento', 'nombre_clinica', 'direccion_clinica', 'ciudad',
        'fecha_minima_reserva', 'preferencia_horario', 'origen_archivo'
    ]

    try:
        # 1. Búsqueda por número de teléfono normalizado
        if phone:
            # Quitar prefijo '+34' y cualquier otro carácter no numérico
            clean_phone = re.sub(r'\D', '', phone)
            if clean_phone.startswith('34'):
                clean_phone = clean_phone[2:]

            sql = f"SELECT {', '.join(campos_lead)} FROM leads WHERE telefono = %s LIMIT 1"
            db_cursor.execute(sql, (clean_phone,))
            result = db_cursor.fetchone()
            if result:
                lead_data = dict(zip(campos_lead, result))
                logger.info(f"Lead encontrado por teléfono para {phone}")
                return lead_data

        # 2. Si no se encuentra por teléfono, buscar por nombre
        if name:
            sql = f"SELECT {', '.join(campos_lead)} FROM leads WHERE nombre_lead = %s LIMIT 1"
            db_cursor.execute(sql, (name,))
            result = db_cursor.fetchone()
            if result:
                lead_data = dict(zip(campos_lead, result))
                logger.info(f"Lead encontrado por nombre para '{name}'")
                return lead_data

        logger.warning(f"No se encontró lead en la BD para tel: {phone} o nombre: '{name}'")
        return {}

    except Exception as e:
        logger.error(f"Error al buscar en la base de datos: {e}")
        return {}

def get_railway_connection():
    """Crea una conexión específica a la BD de Railway usando las variables de entorno del archivo .env."""
    from dotenv import dotenv_values

    # Cargar valores directamente desde el archivo .env
    env_values = dotenv_values()

    # Buscar variables con y sin guion bajo para compatibilidad
    db_host = env_values.get('MYSQL_HOST') or env_values.get('MYSQLHOST')
    db_user = env_values.get('MYSQL_USER') or env_values.get('MYSQLUSER')
    db_password = env_values.get('MYSQL_PASSWORD') or env_values.get('MYSQLPASSWORD')
    db_database = env_values.get('MYSQL_DATABASE') or env_values.get('MYSQLDATABASE')
    db_port = env_values.get('MYSQL_PORT') or env_values.get('MYSQLPORT')

    # Verificar que todas las variables necesarias están presentes
    if not all([db_host, db_user, db_password, db_database, db_port]):
        logger.error("Faltan una o más variables de entorno para la BD de Railway en el archivo .env.")
        logger.error(f"Valores encontrados: HOST={db_host}, USER={db_user}, DB={db_database}, PORT={db_port}")
        return None

    try:
        # Ensure all config values are safe and not None - same safety as db.py
        host = str(db_host) if db_host is not None else 'localhost'
        port = int(db_port) if db_port is not None else 3306
        user = str(db_user) if db_user is not None else 'root'
        password = str(db_password) if db_password is not None else ''
        database = str(db_database) if db_database is not None else 'Segurcaixa'
        
        cfg = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'ssl_disabled': True,
            'autocommit': True,
            'charset': 'utf8mb4',  # Same as db.py - proper unicode support
            'use_unicode': True,   # Same as db.py - get strings instead of bytearrays
            'collation': 'utf8mb4_unicode_ci',
            'sql_mode': 'TRADITIONAL',
            'auth_plugin': 'mysql_native_password',
            'consume_results': True,
            'raise_on_warnings': False
        }

        conn = mysql.connector.connect(**cfg)
        logger.info("Conexión con la base de datos de Railway establecida correctamente.")
        return conn
    except mysql.connector.Error as e:
        logger.error(f"ERROR conectando a la base de datos de Railway: {e}")
        return None

def main():
    """Función principal del script."""
    print("\n" + "="*60)
    print("DESCARGADOR DE GRABACIONES DE LLAMADAS DESDE EXCEL")
    print("="*60)


    db_conn = None
    try:
        # --- 1. Conexiones ---
        logger.info("Inicializando cliente de Pearl AI...")
        pearl_client = get_pearl_client()
        if not pearl_client.test_connection():
            logger.error("No se pudo establecer conexión con la API de Pearl AI. Revisa las credenciales en .env")
            return
        logger.info("Conexión con Pearl AI establecida correctamente.")
        
        # Inicializar la conexión a la base de datos como None
        db_conn = None
        db_cursor = None
        
        # Intentar conectar a la base de datos de Railway específicamente, pero continuar si falla
        try:
            logger.info("Intentando conectar a la base de datos de Railway...")
            # Usar la función get_railway_connection para conectar específicamente a Railway
            db_conn = get_railway_connection()
            if db_conn:
                db_cursor = db_conn.cursor()
                logger.info("Conexión con la base de datos de Railway establecida correctamente.")
            else:
                logger.warning("No se pudo conectar a la base de datos de Railway. El script continuará sin enriquecer los datos.")
        except Exception as e:
            logger.warning(f"Error al conectar a la base de datos de Railway: {str(e)}. El script continuará sin enriquecer los datos.")
            db_conn = None
            db_cursor = None

        # --- 2. Usar información predefinida ---
        excel_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\Grabaciones sept 11.xlsx"
        call_id_column = "Id"

        logger.info(f"Usando archivo Excel predefinido: {excel_path}")
        logger.info(f"Usando columna de Call ID predefinida: '{call_id_column}'")

        if not os.path.exists(excel_path):
            logger.error(f"El archivo no existe: {excel_path}")
            return

        # --- 3. Leer el archivo Excel ---
        logger.info(f"Leyendo el archivo Excel: {excel_path}")
        try:
            df = pd.read_excel(excel_path)
            if call_id_column not in df.columns:
                logger.error(f"La columna '{call_id_column}' no se encuentra en el Excel.")
                logger.info(f"Columnas disponibles: {list(df.columns)}")
                return
        except Exception as e:
            logger.error(f"Error al leer el archivo Excel: {e}")
            return

        call_ids = df[call_id_column].dropna().astype(str).tolist()
        logger.info(f"Se encontraron {len(call_ids)} Call IDs para procesar.")

        # --- 4. Procesar y descargar grabaciones ---
        output_dir = "grabaciones_descargadas"
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Las grabaciones se guardarán en la carpeta: '{output_dir}'")

        success_count = 0
        error_count = 0
        results = []

        for i, call_id in enumerate(call_ids):
            logger.info(f"[{i+1}/{len(call_ids)}] Procesando Call ID: {call_id}")
            status = "ERROR"
            api_response_str = ""
            try:
                # Obtener detalles de la llamada
                call_details = pearl_client.get_call_status(call_id)
                api_response_str = json.dumps(call_details)

                # Intentar descargar la grabación pasando los detalles ya obtenidos
                file_name = f"grabacion_{call_id.replace('/', '_').replace(':', '_')}.wav"
                download_path = os.path.join(output_dir, file_name)

                if os.path.exists(download_path):
                    logger.info(f"La grabación para {call_id} ya existe. Saltando descarga.")
                    status = "SUCCESS (EXISTED)"
                    success_count += 1
                else:
                    result_path = pearl_client.download_recording(call_id, download_path, call_details=call_details)
                    if result_path:
                        logger.info(f"Descarga completada para {call_id}")
                        status = "SUCCESS"
                        success_count += 1
                    elif 'recording' not in call_details or not call_details['recording']:
                        logger.warning(f"No se encontró URL de grabación para {call_id}")
                        status = "NO_RECORDING_URL"
                        error_count += 1
                    else:
                        logger.warning(f"No se pudo descargar la grabación para {call_id}")
                        status = "NO_RECORDING_FILE"
                        error_count += 1

            except PearlAPIError as e:
                logger.error(f"Error de API al procesar {call_id}: {e}")
                api_response_str = str(e)
                error_count += 1
            except Exception as e:
                logger.error(f"Error inesperado al procesar {call_id}: {e}")
                api_response_str = str(e)
                error_count += 1
            
            # Buscar información del lead en la base de datos
            lead_info = {}
            if db_cursor:
                phone_to_search = call_details.get('to')
                name_to_search = call_details.get('name')
                lead_info = _buscar_info_lead(db_cursor, phone_to_search, name_to_search)

            result_row = {
                call_id_column: call_id,
                'download_status': status,
                'api_response': api_response_str
            }
            # Añadir la información del lead al resultado
            result_row.update(lead_info)
            results.append(result_row)

        # --- 5. Guardar resultados en un nuevo Excel ---
        if results:
            results_df = pd.DataFrame(results)
            # Unir con el dataframe original para mantener todos los datos
            # nos aseguramos que la columna de join sea string en ambos dataframes
            df[call_id_column] = df[call_id_column].astype(str)
            results_df[call_id_column] = results_df[call_id_column].astype(str)

            final_df = pd.merge(df, results_df, on=call_id_column, how='left')

            # Guardar el archivo de resultados en el directorio local del proyecto para evitar problemas de permisos
            base_name = os.path.basename(excel_path)
            output_filename = base_name.replace('.xlsx', '_con_resultados.xlsx')
            output_excel_path = os.path.join(os.getcwd(), output_filename)
            try:
                final_df.to_excel(output_excel_path, index=False)
                logger.info(f"Resultados guardados en: {output_excel_path}")
            except Exception as e:
                logger.error(f"Error al guardar el Excel de resultados: {e}")

        # --- 5. Resumen final ---
        print("\n" + "="*60)
        print("PROCESO DE DESCARGA FINALIZADO")
        print("="*60)
        logger.info(f"Total de IDs procesados: {len(call_ids)}")
        logger.info(f"Grabaciones descargadas con éxito: {success_count}")
        logger.info(f"Errores o grabaciones no encontradas: {error_count}")
        logger.info(f"Puedes encontrar los archivos en la carpeta: '{output_dir}'")
        logger.info(f"El log detallado se ha guardado en: {log_filename}")
        print("="*60)

    except Exception as e:
        logger.error(f"Ha ocurrido un error fatal en el script: {e}")
    finally:
        # Cerrar la conexión a la base de datos si está abierta
        if db_conn and hasattr(db_conn, 'is_connected') and db_conn.is_connected():
            try:
                db_conn.close()
                logger.info("Conexión con la base de datos cerrada correctamente.")
            except Exception as e:
                logger.warning(f"Error al cerrar la conexión a la base de datos: {e}")

if __name__ == "__main__":
    main()

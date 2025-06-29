import pandas as pd
import mysql.connector
import os
import logging
from dotenv import load_dotenv
import re

# Configurar logging
log_file = 'railway_data_load.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def load_excel_to_railway(excel_path, db_config):
    """Cargar datos del Excel a la tabla leads en Railway"""
    try:
        # Verificar que el Excel existe
        if not os.path.exists(excel_path):
            logger.error(f"No se encuentra el archivo Excel en {excel_path}")
            return False
        
        # Leer el Excel
        logger.info(f"Leyendo archivo Excel: {excel_path}")
        df = pd.read_excel(excel_path)
        
        # Verificar que el Excel tiene las columnas necesarias
        required_columns = ['NOMBRE_CLINICA', 'DIRECCION_CLINICA', 'areaId']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Faltan columnas en el Excel: {missing_columns}")
            return False
        
        # Conectar a la base de datos
        logger.info("Conectando a la base de datos Railway...")
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Truncar tabla para evitar duplicados si se ejecuta varias veces
        logger.info("Truncando tabla leads...")
        cursor.execute("TRUNCATE TABLE leads")
        
        # Insertar datos
        insert_query = """
        INSERT INTO leads (
            nombre, apellidos, nombre_clinica, direccion_clinica, codigo_postal, ciudad, telefono, 
            area_id, match_source, match_confidence, cita, conPack, ultimo_estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Mapear columnas del Excel a columnas de la tabla
        records = []
        for _, row in df.iterrows():
            nombre = str(row.get('NOMBRE', ''))
            apellidos = str(row.get('APELLIDOS', ''))
            # Extraer código postal y ciudad de la dirección si es posible
            direccion = str(row.get('DIRECCION_CLINICA', ''))
            codigo_postal = ''
            ciudad = ''
            
            # Intentar extraer código postal (formato español: 5 dígitos)
            cp_match = re.search(r'\b\d{5}\b', direccion)
            if cp_match:
                codigo_postal = cp_match.group(0)
            
            # Columnas telefónicas comunes en Excel
            telefono_columns = ['TELEFONO', 'TELÉFONO', 'TLF', 'TEL', 'PHONE']
            telefono = ''
            for col in telefono_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    telefono = str(row.get(col))
                    break
            
            # Buscar columna de fecha de cita si existe
            cita_columns = ['FECHA_CITA', 'CITA', 'FECHA', 'DATE']
            cita_value = None
            for col in cita_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    cita_value = row.get(col)
                    break
            
            # Buscar columna de pack si existe
            pack_columns = ['PACK', 'CONPACK', 'CON_PACK']
            pack_value = False
            for col in pack_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    # Convertir a booleano (True si es 1, 'SI', 'S', 'TRUE', etc.)
                    pack_str = str(row.get(col)).strip().upper()
                    pack_value = pack_str in ['1', 'TRUE', 'SI', 'S', 'YES', 'Y', 'VERDADERO', 'V']
                    break
            
            # Buscar columna de estado si existe
            estado_columns = ['ESTADO', 'STATUS', 'ULTIMO_ESTADO']
            estado_value = None
            for col in estado_columns:
                if col in df.columns and pd.notna(row.get(col)):
                    estado_str = str(row.get(col)).strip().lower()
                    # Normalizar valores de estado
                    if 'no answer' in estado_str or 'noanswer' in estado_str or 'no' in estado_str:
                        estado_value = 'no answer'
                    elif 'busy' in estado_str or 'ocupado' in estado_str:
                        estado_value = 'busy'
                    elif 'complete' in estado_str or 'completado' in estado_str or 'finalizado' in estado_str:
                        estado_value = 'completed'
                    break
            
            record = (
                nombre,
                apellidos,
                row.get('NOMBRE_CLINICA', ''),
                direccion,
                codigo_postal,
                ciudad,
                telefono,
                row.get('areaId', ''),
                row.get('match_source', ''),
                row.get('match_confidence', 0),
                cita_value,
                pack_value,
                estado_value
            )
            records.append(record)
        
        # Insertar todos los registros
        logger.info(f"Insertando {len(records)} registros en la tabla leads...")
        cursor.executemany(insert_query, records)
        connection.commit()
        
        logger.info(f"Se insertaron {cursor.rowcount} registros en la tabla 'leads'")
        
        # Verificar que se insertaron los datos
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        logger.info(f"Total registros en leads después de la inserción: {count}")
        
        # Cerrar conexión
        cursor.close()
        connection.close()
        logger.info("Conexión cerrada")
        
        return True
    except Exception as e:
        logger.error(f"Error al cargar datos: {e}")
        return False

if __name__ == "__main__":
    print(f"Iniciando carga de datos. Los logs se guardarán en {log_file}")
    
    # Solicitar información de conexión a Railway
    print("\nPor favor, introduce los datos de conexión a tu base de datos Railway:")
    host = input("Host (ej: containers-us-west-XXX.railway.app): ")
    port = input("Puerto (ej: 7051): ")
    user = input("Usuario (por defecto 'root'): ") or "root"
    password = input("Contraseña: ")
    database = input("Base de datos (por defecto 'railway'): ") or "railway"
    
    # Configurar conexión
    db_config = {
        'host': host,
        'port': int(port),
        'user': user,
        'password': password,
        'database': database
    }
    
    # Ruta al archivo Excel
    excel_path = os.environ.get('EXCEL_PATH', r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\01NP Dental_Piloto_VoiceBot_20250603_TeYame_con_areaId.xlsx")
    
    # Preguntar por la ruta si no está configurada
    if not os.path.exists(excel_path):
        excel_path = input("Introduce la ruta completa al archivo Excel: ")
    
    # Cargar datos
    print(f"\nIniciando carga de datos desde {excel_path}...")
    result = load_excel_to_railway(excel_path, db_config)
    
    if result:
        print("\n¡Datos cargados correctamente!")
    else:
        print("\nError al cargar los datos.")
    
    print(f"\nProceso completado. Revisa el archivo de log {log_file} para más detalles.")

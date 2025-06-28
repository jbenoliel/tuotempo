import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()
def create_connection(include_db=True):
    """Crear conexión a MySQL compatible con Railway y local"""
    try:
        db_config = {
            'host': os.environ.get('MYSQLHOST') or os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQLUSER') or os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQLPASSWORD') or os.environ.get('MYSQL_PASSWORD', ''),
            'port': int(os.environ.get('MYSQLPORT') or os.environ.get('MYSQL_PORT', 3306)),
            'auth_plugin': 'mysql_native_password'
        }
        if include_db:
            db_config['database'] = os.environ.get('MYSQLDATABASE') or os.environ.get('MYSQL_DATABASE', '')
        connection = mysql.connector.connect(**db_config)
        print("Conexión a MySQL establecida correctamente")
        return connection
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def create_database(connection, db_name):
    """Crear base de datos si no existe"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Base de datos '{db_name}' creada correctamente o ya existía")
        return True
    except Error as e:
        print(f"Error al crear base de datos: {e}")
        return False

def create_table(connection, db_name):
    """Crear tabla para almacenar los datos de los leads"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"USE {db_name}")
        cursor.execute("DROP TABLE IF EXISTS leads")

        create_table_query = (
            "CREATE TABLE leads ("
            "id INT AUTO_INCREMENT PRIMARY KEY,"
            "nombre VARCHAR(100),"
            "apellidos VARCHAR(150),"
            "nombre_clinica VARCHAR(255),"
            "direccion_clinica VARCHAR(255),"
            "codigo_postal VARCHAR(10),"
            "ciudad VARCHAR(100),"
            "telefono VARCHAR(20),"
            "area_id VARCHAR(100),"
            "match_source VARCHAR(50),"
            "match_confidence INT,"
            "cita DATETIME NULL,"
            "conPack BOOLEAN DEFAULT FALSE,"
            "ultimo_estado ENUM('no answer', 'busy', 'completed') NULL"
            ")"
        )
        cursor.execute(create_table_query)
        print("Tabla 'leads' creada correctamente o ya existía")
        return True
    except Error as e:
        print(f"Error al crear tabla: {e}")
        return False
        
def insert_data_from_excel(connection, db_name, excel_path):
    """Insertar datos del Excel en la tabla"""
    try:
        # Leer el Excel
        print(f"Leyendo archivo Excel: {excel_path}")
        df = pd.read_excel(excel_path)
        
        # Verificar que el Excel tiene las columnas necesarias
        required_columns = ['NOMBRE_CLINICA', 'DIRECCION_CLINICA', 'areaId']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Error: Faltan columnas en el Excel: {missing_columns}")
            return False
        
        # Conectar a la base de datos
        cursor = connection.cursor()
        cursor.execute(f"USE {db_name}")
        
        # Truncar tabla para evitar duplicados si se ejecuta varias veces
        cursor.execute("TRUNCATE TABLE leads")
        
        # Insertar datos
        insert_query = """
        INSERT INTO leads (
            nombre, apellidos, nombre_clinica, direccion_clinica, codigo_postal, ciudad, telefono, 
            area_id, match_source, match_confidence, cita, conPack, ultimo_estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Mapear columnas del Excel a columnas de la tabla
        # Ajustar según las columnas reales del Excel
        records = []
        for _, row in df.iterrows():
            nombre = str(row.get('NOMBRE', ''))
            apellidos = str(row.get('APELLIDOS', ''))
            # Extraer código postal y ciudad de la dirección si es posible
            direccion = str(row.get('DIRECCION_CLINICA', ''))
            codigo_postal = ''
            ciudad = ''
            
            # Intentar extraer código postal (formato español: 5 dígitos)
            import re
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
        cursor.executemany(insert_query, records)
        connection.commit()
        
        print(f"Se insertaron {cursor.rowcount} registros en la tabla 'leads'")
        return True
    except Error as e:
        print(f"Error al insertar datos: {e}")
        return False
    except Exception as e:
        print(f"Error general: {e}")
        return False

def download_excel_from_url(url, save_path):
    """Descargar Excel desde una URL"""
    try:
        import requests
        print(f"Descargando Excel desde: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Excel descargado correctamente a: {save_path}")
        return True
    except Exception as e:
        print(f"Error al descargar el Excel: {e}")
        return False

def main():
    # Configuración
    db_name = os.environ.get('MYSQLDATABASE') or os.environ.get('MYSQL_DATABASE', 'Segurcaixa')
    
    # Opciones para obtener el Excel
    excel_url = os.environ.get('EXCEL_URL', '')
    excel_path = os.environ.get('EXCEL_PATH', r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\01NP Dental_Piloto_VoiceBot_20250603_TeYame_con_areaId.xlsx")
    
    # Si estamos en Railway y tenemos URL, descargar el Excel
    if excel_url and ('RAILWAY_ENVIRONMENT' in os.environ or not os.path.exists(excel_path)):
        temp_excel_path = '/tmp/datos_clinicas.xlsx'
        if not download_excel_from_url(excel_url, temp_excel_path):
            print("No se pudo descargar el Excel. Abortando.")
            return
        excel_path = temp_excel_path
    
    # Verificar que el Excel existe
    if not os.path.exists(excel_path):
        print(f"Error: No se encuentra el archivo Excel en {excel_path}")
        print("Por favor, configura EXCEL_URL o EXCEL_PATH en las variables de entorno.")
        return

    # 1. Conexión SIN base de datos para crearla
    connection = create_connection(include_db=False)
    if not connection:
        return

    # Crear base de datos
    if not create_database(connection, db_name):
        connection.close()
        return
    connection.close()

    # 2. Conexión CON base de datos para el resto
    connection = create_connection(include_db=True)
    if not connection:
        return

    # Crear tabla
    if not create_table(connection, db_name):
        connection.close()
        return

    # Insertar datos del Excel
    if not insert_data_from_excel(connection, db_name, excel_path):
        connection.close()
        return

    print("¡Base de datos y datos importados correctamente!")
    connection.close()
    
    print("\nProceso completado correctamente.")
    print(f"Los datos se han importado a la base de datos MySQL '{db_name}' en la tabla 'leads'.")
    
    # Cerrar conexión
    if connection.is_connected():
        connection.close()
        print("Conexión a MySQL cerrada")

if __name__ == "__main__":
    main()

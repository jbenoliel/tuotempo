import pandas as pd
from flask import url_for, current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

def generate_reset_token(user_id):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(user_id, salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'my_precious_salt'))

def send_password_reset_email(user_email, user_id):
    from app_dashboard import mail # Importación local para evitar importación circular
    token = generate_reset_token(user_id)
    reset_url = url_for('main.reset_password_with_token', token=token, _external=True)
    
    subject = "Restablecimiento de contraseña - TuoTempo"
    html_body = f"""
    <p>Hola,</p>
    <p>Has solicitado restablecer tu contraseña para tu cuenta en TuoTempo.</p>
    <p>Por favor, haz clic en el siguiente enlace para establecer una nueva contraseña:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Si no has solicitado esto, por favor ignora este email.</p>
    <p>Gracias,</p>
    <p>El equipo de TuoTempo</p>
    """
    
    msg = Message(subject, recipients=[user_email], html=html_body)
    mail.send(msg)

def verify_reset_token(token, max_age_seconds=1800):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = serializer.loads(
            token,
            salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'my_precious_salt'),
            max_age=max_age_seconds
        )
    except Exception:
        return None
    return user_id


import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def load_excel_data(connection, source, origen_archivo=None):
    logger.info(f"Iniciando carga de datos desde: {source}")
    
    # Determinar el nombre del archivo origen
    if origen_archivo is None:
        if isinstance(source, str):
            # Extraer el nombre del archivo sin extensión
            origen_archivo = os.path.splitext(os.path.basename(source))[0].upper()
        else:
            # Para BytesIO usar timestamp
            origen_archivo = f"UPLOAD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Archivo origen determinado: {origen_archivo}")
    
    try:
        if isinstance(source, str):
            df = pd.read_excel(source) if source.endswith('.xlsx') else pd.read_csv(source)
        else:
            df = pd.read_excel(source) # Para BytesIO
    except Exception as e:
        logger.error(f"Error al leer el archivo Excel/CSV: {e}")
        return {'insertados': 0, 'actualizados': 0, 'errores': 0, 'total': 0}

    # Lógica de mapeo de columnas y carga de datos...
    # (Esta es la lógica que ya tenías en app_dashboard.py)
    db_to_excel_map = {
        'nombre': ['nombre', 'name', 'first name', 'firstname'],
        'apellidos': ['apellidos', 'surname', 'last name', 'lastname'],
        'telefono': ['teléfono', 'telefono', 'telefono1', 'teléfono1', 'phone', 'mobile', 'phone number', 'tel', 'teléfono móvil', 'teléfono principal', 'teléfono contacto', 'teléfono cliente', 'número', 'número teléfono'],
        'telefono2': ['teléfono2', 'telefono2', 'telefono 2', 'teléfono 2', 'phone2', 'mobile2', 'telefono secundario', 'tel2', 'teléfono alternativo', 'otro teléfono'],
        'nif': ['nif', 'dni', 'documento'],
        'fecha_nacimiento': ['fecha nacimiento', 'fecha_nacimiento', 'birth date'],
        'sexo': ['sexo', 'gender'],
        'certificado': ['certificado', 'certificate'],
        'clinica_id': ['clinica id', 'clinica_id', 'clinic id'],
        'delegacion': ['delegacion', 'delegation'],
        'poliza': ['poliza', 'policy'],
        'segmento': ['segmento', 'segment'],
        'email': ['email', 'correo electronico'],
        'cita': ['cita', 'fecha_cita', 'fecha cita', 'appointment date'],
        'nombre_clinica': ['nombre_clinica', 'nombre clinica', 'clinic name'],
        'direccion_clinica': ['direccion_clinica', 'direccion clinica', 'clinic address'],
        'codigo_postal': ['codigo_postal', 'codigo postal', 'postal code'],
        'ciudad': ['ciudad', 'city'],
    }

    normalized_excel_cols = {re.sub(r'[^a-z0-9]+', '', str(col).lower().strip()): str(col) for col in df.columns}
    excel_to_db_map = {}
    for db_col, aliases in db_to_excel_map.items():
        for alias in aliases:
            norm_alias = re.sub(r'[^a-z0-9]+', '', alias.lower().strip())
            if norm_alias in normalized_excel_cols:
                excel_to_db_map[normalized_excel_cols[norm_alias]] = db_col
                break
    
    df.rename(columns=excel_to_db_map, inplace=True)

    # --- Inserción real en MySQL ---
    # Columnas exactas de la tabla leads (incluyendo origen_archivo)
    leads_cols = [
        'nombre', 'apellidos', 'nombre_clinica', 'direccion_clinica', 'codigo_postal',
        'ciudad', 'telefono', 'area_id', 'match_source', 'match_confidence', 'cita',
        'conPack', 'ultimo_estado', 'resultado_llamada', 'telefono2', 'call_id',
        'call_time', 'call_duration', 'call_summary', 'call_recording_url',
        'status_level_1', 'status_level_2', 'hora_rellamada', 'error_tecnico',
        'razon_vuelta_a_llamar', 'razon_no_interes', 'certificado',
        'clinica_id', 'delegacion', 'fecha_nacimiento', 'nif', 'orden', 'poliza',
        'segmento', 'sexo', 'origen_archivo'
    ]

    # Asegurar que todos los campos existen en el DataFrame
    for col in leads_cols:
        if col not in df.columns:
            if col == 'origen_archivo':
                df[col] = origen_archivo  # Asignar el nombre del archivo origen
            else:
                df[col] = None

    # Preprocesar teléfonos para asegurar que se importan correctamente
    if 'telefono' in df.columns:
        # Convertir NaN a None
        df['telefono'] = df['telefono'].apply(lambda x: str(x).strip() if pd.notna(x) else None)
        # Eliminar caracteres no numéricos pero mantener el + inicial si existe
        df['telefono'] = df['telefono'].apply(lambda x: re.sub(r'[^0-9+]', '', str(x)) if pd.notna(x) else None)
        # Asegurar que hay al menos un dígito
        df['telefono'] = df['telefono'].apply(lambda x: x if pd.notna(x) and re.search(r'\d', str(x)) else None)
        
    if 'telefono2' in df.columns:
        df['telefono2'] = df['telefono2'].apply(lambda x: str(x).strip() if pd.notna(x) else None)
        df['telefono2'] = df['telefono2'].apply(lambda x: re.sub(r'[^0-9+]', '', str(x)) if pd.notna(x) else None)
        df['telefono2'] = df['telefono2'].apply(lambda x: x if pd.notna(x) and re.search(r'\d', str(x)) else None)
    
    # Reordenar columnas y convertir booleanos/tinyint
    df = df[leads_cols]
    if 'conPack' in df.columns:
        df['conPack'] = df['conPack'].apply(lambda x: 1 if str(x).strip().lower() in ['1', 'si', 'sí', 'true', 'yes'] else 0)

    registros = []
    for _, row in df.iterrows():
        registros.append(tuple(row[col] if pd.notna(row[col]) else None for col in leads_cols))

    insertados, errores = 0, 0
    if registros:
        placeholders = ','.join(['%s'] * len(leads_cols))
        cols_sql = ','.join(leads_cols)
        sql = f"INSERT INTO leads ({cols_sql}) VALUES ({placeholders})"
        try:
            with connection.cursor() as cursor:
                cursor.executemany(sql, registros)
            connection.commit()
            insertados = len(registros)
            
            # Registrar/actualizar archivo origen
            try:
                _registrar_archivo_origen(connection, origen_archivo, insertados)
            except Exception as e:
                logger.warning(f"Error registrando archivo origen: {e}")
            
        except Exception as e:
            logger.error(f"Error insertando registros: {e}", exc_info=True)
            errores = len(registros)
    logger.info(f"Insertados: {insertados} | Errores: {errores}")

    return {
        'insertados': insertados,
        'actualizados': 0,
        'errores': errores,
        'total': len(df)
    }

def _registrar_archivo_origen(connection, nombre_archivo, registros_importados):
    """
    Registra o actualiza un archivo en la tabla archivos_origen.
    """
    try:
        with connection.cursor() as cursor:
            # Verificar si el archivo ya existe
            cursor.execute("SELECT id, total_registros FROM archivos_origen WHERE nombre_archivo = %s", (nombre_archivo,))
            resultado = cursor.fetchone()
            
            if resultado:
                # Actualizar registro existente
                archivo_id, total_anterior = resultado
                nuevo_total = total_anterior + registros_importados
                cursor.execute("""
                    UPDATE archivos_origen 
                    SET total_registros = %s, fecha_creacion = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (nuevo_total, archivo_id))
                logger.info(f"Archivo origen '{nombre_archivo}' actualizado: {total_anterior} -> {nuevo_total} registros")
            else:
                # Crear nuevo registro
                cursor.execute("""
                    INSERT INTO archivos_origen (nombre_archivo, descripcion, total_registros, usuario_creacion)
                    VALUES (%s, %s, %s, %s)
                """, (nombre_archivo, f"Importación automática de {nombre_archivo}", registros_importados, "sistema"))
                logger.info(f"Nuevo archivo origen '{nombre_archivo}' registrado con {registros_importados} registros")
            
            connection.commit()
    except Exception as e:
        logger.error(f"Error en _registrar_archivo_origen: {e}")
        raise

def exportar_datos_completos(connection):
    """
    Exporta las tablas 'leads' y 'pearl_calls' a un único archivo Excel con dos pestañas.
    """
    try:
        # 1. Definir el directorio y crear el nombre del archivo
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_completo_{timestamp}.xlsx"
        filepath = os.path.join(data_dir, filename)

        # 2. Leer ambas tablas en DataFrames de pandas
        df_leads = pd.read_sql("SELECT * FROM leads", connection)
        if df_leads.empty:
            # Fallback por si read_sql falla silenciosamente con mysql.connector
            logger.warning("pd.read_sql devolvió 0 registros; usando cursor manual como fallback")
            with connection.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM leads")
                rows = cur.fetchall()
                df_leads = pd.DataFrame(rows)
        logger.info(f"Leídos {len(df_leads)} registros de la tabla 'leads'.")
        df_calls = pd.read_sql("SELECT * FROM pearl_calls", connection)
        logger.info(f"Leídos {len(df_calls)} registros de la tabla 'pearl_calls'.")

        # 3. Usar pd.ExcelWriter para crear el archivo con dos pestañas
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df_leads.to_excel(writer, sheet_name='Leads', index=False)
            df_calls.to_excel(writer, sheet_name='Llamadas', index=False)
        
        logger.info(f"Datos exportados a {filepath} con {len(df_leads)} leads y {len(df_calls)} llamadas.")
        return True, filepath
    except Exception as e:
        error_msg = f"Error al exportar los datos completos: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

from db import get_connection

def get_statistics(filtro_origen_archivo=None):
    """Calcula estadísticas en tiempo real para el dashboard.
    
    Args:
        filtro_origen_archivo (str|list): Filtro por archivo origen. 
                                          Puede ser un string, lista de strings, o None para todos.
    """
    stats = {
        'total_leads': 0,
        'llamadas_hoy': 0,
        'contactados': 0,
        'conversion_rate': '0%',
        'citas_contactados_rate': '0%',
        'citas_total': 0,
        'estados': {
            'volver_llamar': 0,
            'no_interesado': 0,
            'cita_sin_pack': 0,
            'cita_con_pack': 0
        },
        'filtro_origen': filtro_origen_archivo,  # Incluir info del filtro aplicado
        'archivos_disponibles': []  # Lista de archivos disponibles para el selector
    }

    conn = get_connection()
    if not conn:
        logger.warning("No se pudo obtener conexión a la BD; devolviendo estadísticas vacías")
        return stats

    try:
        with conn.cursor(dictionary=True) as cursor:
            # Obtener lista de archivos disponibles
            cursor.execute("SELECT nombre_archivo, total_registros FROM archivos_origen WHERE activo = 1 ORDER BY nombre_archivo")
            stats['archivos_disponibles'] = cursor.fetchall()
            
            # Construir cláusula WHERE para filtro de archivo origen
            where_clause = ""
            params = []
            
            if filtro_origen_archivo:
                if isinstance(filtro_origen_archivo, str):
                    where_clause = "WHERE origen_archivo = %s"
                    params = [filtro_origen_archivo]
                elif isinstance(filtro_origen_archivo, list) and filtro_origen_archivo:
                    placeholders = ','.join(['%s'] * len(filtro_origen_archivo))
                    where_clause = f"WHERE origen_archivo IN ({placeholders})"
                    params = filtro_origen_archivo
            
            # Total leads con filtro
            query_total = f"SELECT COUNT(*) AS cnt FROM leads {where_clause}"
            cursor.execute(query_total, params)
            stats['total_leads'] = cursor.fetchone()['cnt']

            # Llamadas de hoy (temporalmente deshabilitado)
            stats['llamadas_hoy'] = 0

            # Resumen de estados solicitados (status_level_1 + conPack) con filtro
            query_estados = f"""
                SELECT
                    IFNULL(SUM(CASE WHEN status_level_1 IS NOT NULL AND status_level_1 <> '' THEN 1 ELSE 0 END), 0) AS contactados,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Volver a llamar' THEN 1 ELSE 0 END), 0) AS volver_llamar,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'No Interesado' THEN 1 ELSE 0 END), 0) AS no_interesado,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND (conPack IS NULL OR conPack = 0) THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND conPack = 1 THEN 1 ELSE 0 END), 0) AS cita_con_pack
                FROM leads {where_clause}
            """
            cursor.execute(query_estados, params)
            row_states = cursor.fetchone()
            stats['contactados'] = row_states['contactados']
            stats['estados'] = {
                'volver_llamar': row_states['volver_llamar'],
                'no_interesado': row_states['no_interesado'],
                'cita_sin_pack': row_states['cita_sin_pack'],
                'cita_con_pack': row_states['cita_con_pack']
            }

            # Calcular total de citas y tasa sobre contactados
            stats['citas_total'] = row_states['cita_sin_pack'] + row_states['cita_con_pack']

            if stats['contactados']:
                stats['citas_contactados_rate'] = f"{(stats['citas_total'] / stats['contactados'] * 100):.0f}%"
            else:
                stats['citas_contactados_rate'] = '0%'

            # Definir todos los posibles subestados según la tabla proporcionada
            subestados_volver_posibles = [
                'buzón', 'no disponible cliente', 'Interesado. Problema técnico'
            ]
            
            subestados_no_interes_posibles = [
                'no disponibilidad cliente', 'a corto plazo (vac. Trab...)..)', 
                'Descontento con Adeslas', 'No da motivos', 'Próxima baja'
            ]
            
            # Subestados para CONFIRMADO (Citas)
            subestados_confirmado = ['Con Pack', 'Sin Pack']
            
            # Ya ha ido a la clínica (sin subestados)
            
            # Subestados para volver a llamar
            cursor.execute("SELECT IFNULL(status_level_2, 'Sin especificar') AS sub, COUNT(*) AS cnt FROM leads WHERE TRIM(status_level_1) = 'Volver a llamar' GROUP BY sub")
            subestados_volver_actual = {r['sub']: r['cnt'] for r in cursor.fetchall()}
            
            # Asegurar que todos los posibles subestados estén incluidos
            stats['subestados_volver'] = {sub: subestados_volver_actual.get(sub, 0) for sub in subestados_volver_posibles}
            
            # Subestados para no interesado
            cursor.execute("SELECT IFNULL(status_level_2, 'Sin especificar') AS sub, COUNT(*) AS cnt FROM leads WHERE TRIM(status_level_1) = 'No Interesado' GROUP BY sub")
            subestados_no_interes_actual = {r['sub']: r['cnt'] for r in cursor.fetchall()}
            
            # Asegurar que todos los posibles subestados estén incluidos
            stats['subestados_no_interes'] = {sub: subestados_no_interes_actual.get(sub, 0) for sub in subestados_no_interes_posibles}

            # Estadísticas diarias (temporalmente deshabilitado)
            stats['diarios'] = []      
            

            # Tasa de conversión simple: leads con conPack=1 sobre total
            if stats['total_leads']:
                cursor.execute("SELECT COUNT(*) AS cnt FROM leads WHERE conPack = 1")
                conversion = cursor.fetchone()['cnt'] / stats['total_leads'] * 100
                stats['conversion_rate'] = f"{conversion:.0f}%"
    except Exception as e:
        logger.error(f"Error calculando estadísticas: {e}")
    finally:
        conn.close()

    return stats

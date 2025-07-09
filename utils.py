import pandas as pd
import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def load_excel_data(connection, source):
    logger.info(f"Iniciando carga de datos desde: {source}")
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
        'telefono': ['teléfono', 'telefono', 'phone', 'mobile', 'phone number'],
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
    # Columnas exactas de la tabla leads (en el mismo orden que el INSERT)
    leads_cols = [
        'nombre', 'apellidos', 'nombre_clinica', 'direccion_clinica', 'codigo_postal',
        'ciudad', 'telefono', 'area_id', 'match_source', 'match_confidence', 'cita',
        'conPack', 'ultimo_estado', 'resultado_llamada', 'telefono2', 'call_id',
        'call_time', 'call_duration', 'call_summary', 'call_recording_url',
        'status_level_1', 'status_level_2', 'hora_rellamada', 'error_tecnico',
        'razon_vuelta_a_llamar', 'razon_no_interes', 'certificado',
        'clinica_id', 'delegacion', 'fecha_nacimiento', 'nif', 'orden', 'poliza',
        'segmento', 'sexo'
    ]

    # Asegurar que todos los campos existen en el DataFrame
    for col in leads_cols:
        if col not in df.columns:
            df[col] = None

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

def exportar_tabla_leads(connection):
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        df = pd.read_sql("SELECT * FROM leads", connection)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_backup_{timestamp}.xlsx"
        filepath = os.path.join(data_dir, filename)
        df.to_excel(filepath, index=False)
        logger.info(f"Tabla leads exportada a {filepath} con {len(df)} registros")
        return True, filepath
    except Exception as e:
        error_msg = f"Error al exportar tabla leads: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

from db import get_connection

def get_statistics():
    """Calcula estadísticas en tiempo real para el dashboard."""
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
        }
    }

    conn = get_connection()
    if not conn:
        logger.warning("No se pudo obtener conexión a la BD; devolviendo estadísticas vacías")
        return stats

    try:
        with conn.cursor(dictionary=True) as cursor:
            # Total leads
            cursor.execute("SELECT COUNT(*) AS cnt FROM leads")
            stats['total_leads'] = cursor.fetchone()['cnt']

            # Llamadas de hoy (temporalmente deshabilitado)
            stats['llamadas_hoy'] = 0

            # Resumen de estados solicitados (status_level_1 + conPack)
            cursor.execute("""
                SELECT
                    IFNULL(SUM(CASE WHEN status_level_1 IS NOT NULL AND status_level_1 <> '' THEN 1 ELSE 0 END), 0) AS contactados,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Volver a llamar' THEN 1 ELSE 0 END), 0) AS volver_llamar,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'No Interesado' THEN 1 ELSE 0 END), 0) AS no_interesado,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND (conPack IS NULL OR conPack = 0) THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                    IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND conPack = 1 THEN 1 ELSE 0 END), 0) AS cita_con_pack
                FROM leads
            """)
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

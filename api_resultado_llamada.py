import mysql.connector
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from config import settings
import mysql.connector

# Cargar variables de entorno si existe un archivo .env
load_dotenv()

# Configurar logger PRIMERO
logger = logging.getLogger(__name__)

# Importar scheduler para integración
try:
    from call_scheduler import CallScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    logger.warning("CallScheduler no disponible")
    SCHEDULER_AVAILABLE = False

# Importar sistema de notificaciones
try:
    from email_notifications import send_cita_notification
    EMAIL_NOTIFICATIONS_AVAILABLE = True
    logger.info("Sistema de notificaciones por email disponible")
except ImportError:
    logger.warning("Sistema de notificaciones por email no disponible")
    EMAIL_NOTIFICATIONS_AVAILABLE = False

# Crear un Blueprint en lugar de una app. Todas las rutas aquí definidas
# colgarán del prefijo /api que se registra en la app principal.
resultado_api = Blueprint('resultado_api', __name__)

# Configuración de la base de datos usando settings
DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_DATABASE,
    'ssl_disabled': True,  # Deshabilitar SSL para evitar errores de conexión
    'autocommit': True,
    'charset': 'utf8mb4',
    'use_unicode': True
}

def get_db_connection():
    """Establece conexión con la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Error conectando a MySQL: {err}")
        # Si falla con SSL, intentar sin SSL
        if 'SSL' in str(err) or '2026' in str(err):
            try:
                logger.info("Intentando conexión sin SSL...")
                config_no_ssl = DB_CONFIG.copy()
                config_no_ssl['ssl_disabled'] = True
                connection = mysql.connector.connect(**config_no_ssl)
                return connection
            except mysql.connector.Error as err2:
                logger.error(f"Error conectando sin SSL: {err2}")
        return None

@resultado_api.route('/api/status', methods=['GET'])
def status():
    """Endpoint para verificar el estado de la API"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service": "API Resultado Llamada"
    })

@resultado_api.route('/api/actualizar_resultado', methods=['POST'])
def actualizar_resultado():
    """
    Actualiza el resultado y los datos de una llamada para un lead específico.
    Este endpoint recibe datos de la llamada desde un sistema externo (como NLPearl) y los guarda en la BD.
    """
    data = request.json
    logger.info(f"Recibida petición para actualizar resultado: {data}")

    # Validar datos requeridos
    if not data or not data.get('telefono'):
        logger.error("Petición rechazada: No se proporcionó número de teléfono.")
        return jsonify({"error": "Se requiere el número de teléfono"}), 400

    import re
    telefono_raw = str(data.get('telefono'))
    # Eliminar caracteres no numéricos
    telefono_digits = re.sub(r'\D', '', telefono_raw)
    # Conservar los 9 dígitos finales (núm. nacional) si sobran
    if len(telefono_digits) > 9:
        telefono_digits = telefono_digits[-9:]
    telefono = telefono_digits

    # -------------------------------------------------------------
    # 1. Extracción de parámetros adicionales y reglas de negocio
    # -------------------------------------------------------------
    buzon = data.get('buzon')                      # True si se cayó en buzón
    volver_a_llamar_flag = data.get('volverALlamar')  # True si se debe volver a llamar

    codigo_no_interes = data.get('codigoNoInteres')
    # Permitir que venga como lista
    if isinstance(codigo_no_interes, list):
        codigo_no_interes = codigo_no_interes[0] if codigo_no_interes else None
    codigo_volver_llamar = data.get('codigoVolverLlamar')
    
    # Nuevos campos de preferencia del paciente
    preferencia_mt = data.get('preferenciaMT')      # MORNING o AFTERNOON
    preferencia_fecha = data.get('preferenciaFecha')  # Fecha deseada por el paciente

    # Mapas de traducción de códigos compactos → descripciones (ACTUALIZADOS)
    mapa_no_interes = {
        # Nuevas razones de no interés de Pearl AI
        'paciente_con_tratamiento': 'Paciente con tratamiento',
        'paciente_con_tratamiento_particular': 'Paciente con tratamiento particular', 
        'llamara_cuando_este_interesado': 'Llamará cuando esté interesado',
        'solicitan_baja_poliza': 'Solicitan baja póliza',
        'no_desea_informar_motivo': 'No desea informar motivo / no colabora',
        # LEGACY - mantener compatibilidad con códigos anteriores
        'no disponibilidad': 'no disponibilidad cliente',
        'descontento': 'Descontento con Adeslas',
        'bajaProxima': 'Próxima baja',
        'otros': 'No da motivos'
    }

    mapa_volver_llamar = {
        'buzon': 'buzón',
        'interrupcion': 'no disponible cliente',
        'proble tecnico': 'Interesado. Problema técnico',
        'proble_tecnico': 'Interesado. Problema técnico'
    }
    
    # NUEVOS MAPAS para estados específicos de Pearl AI
    mapa_utiles_positivos = {
        'cita_sin_pack': {
            'status_level_1': 'Cita Agendada',
            'status_level_2': 'Sin Pack'
        },
        'cita_con_pack': {
            'status_level_1': 'Cita Agendada', 
            'status_level_2': 'Con Pack'
        }
    }
    
    mapa_utiles_negativos = {
        'paciente_con_tratamiento': {
            'status_level_1': 'No Interesado',
            'status_level_2': 'Paciente con tratamiento'
        },
        'paciente_con_tratamiento_particular': {
            'status_level_1': 'No Interesado',
            'status_level_2': 'Paciente con tratamiento particular'
        },
        'llamara_cuando_este_interesado': {
            'status_level_1': 'Volver a llamar',
            'status_level_2': 'Llamará cuando esté interesado'
        },
        'solicita_baja_poliza': {
            'status_level_1': 'No Interesado',
            'status_level_2': 'Solicita baja póliza'
        },
        'no_quiere_ser_molestado': {
            'status_level_1': 'No Interesado',
            'status_level_2': 'No quiere ser molestado / no colabora'
        },
        'no_colabora': {
            'status_level_1': 'No Interesado',
            'status_level_2': 'No quiere ser molestado / no colabora'
        }
    }

    # -------------------------------------------------------------
    # 2. Deducción automática de status_level_1 y status_level_2
    # -------------------------------------------------------------
    status_level_1 = None
    status_level_2 = None

    # NUEVA LÓGICA: Usar parámetros existentes del JSON para mapear a nuevos estados
    
    # Identificar si es útil positivo usando parámetros existentes
    # MEJORADO: Detectar citas por múltiples criterios
    call_result = data.get('callResult', '').lower()
    fecha_deseada = data.get('fechaDeseada')
    preferencia_mt = data.get('preferenciaMT')
    
    # Criterios para detectar cita:
    # 1. Campos tradicionales (nuevaCita, conPack)
    # 2. callResult explícito ("cita agendada", "cita confirmada")  
    # 3. Solo presencia de fechaDeseada + preferenciaMT (indica intención de cita)
    is_appointment = (
        data.get('nuevaCita') or 
        data.get('conPack') or
        call_result in ['cita agendada', 'citaagendada', 'cita confirmada', 'citaconfirmada'] or
        (fecha_deseada and preferencia_mt)  # NUEVO: detectar solo por estos campos
    )
    
    if is_appointment:
        # ÚTILES POSITIVOS - acepta cita
        # Solo marcar "Con Pack" si específicamente viene conPack: true
        if data.get('conPack') is True:
            status_level_1 = 'Cita Agendada'
            status_level_2 = 'Con Pack'
            logger.info(f"Estado útil positivo: Cita con pack (conPack=true)")
        else:
            status_level_1 = 'Cita Agendada'
            status_level_2 = 'Sin Pack'
            reason = f"callResult: '{call_result}'" if call_result else "fechaDeseada/preferenciaMT/interesado"
            logger.info(f"Estado útil positivo: Cita sin pack ({reason})")
            
    # Identificar si es útil negativo usando códigos existentes
    elif data.get('noInteresado') or codigo_no_interes:
        # ÚTILES NEGATIVOS - mapear códigos existentes a nuevos estados específicos
        if codigo_no_interes == 'paciente_tratamiento':
            status_level_1 = 'No Interesado'
            status_level_2 = 'Paciente con tratamiento'
        elif codigo_no_interes == 'paciente_tratamiento_particular':
            status_level_1 = 'No Interesado'
            status_level_2 = 'Paciente con tratamiento particular'
        elif codigo_no_interes == 'solicita_baja':
            status_level_1 = 'No Interesado'
            status_level_2 = 'Solicita baja póliza'
        elif codigo_no_interes == 'no_colabora':
            status_level_1 = 'No Interesado'
            status_level_2 = 'No quiere ser molestado / no colabora'
        else:
            # Usar mapeo legacy existente
            status_level_1 = 'No Interesado'
            status_level_2 = mapa_no_interes.get(codigo_no_interes, data.get('razonNoInteres', 'No da motivos'))
        
        logger.info(f"Estado útil negativo aplicado: {codigo_no_interes} -> {status_level_1} / {status_level_2}")
    
    # Caso especial: "Llamará cuando esté interesado" 
    elif data.get('llamaraInteresado'):
        status_level_1 = 'Volver a llamar'
        status_level_2 = 'Llamará cuando esté interesado'
        logger.info(f"Estado especial: Llamará cuando esté interesado")
        
    # LÓGICA LEGACY (mantener compatibilidad con versiones anteriores)
    elif data.get('nuevaCita'):
        # Una nueva cita siempre se considera un Éxito
        status_level_1 = 'Cita Agendada'
        status_level_2 = 'Cita programada'
    elif buzon:
        status_level_1 = 'Volver a llamar'
        status_level_2 = 'buzón'
    elif data.get('errorTecnico'):
        status_level_1 = 'Volver a llamar'
        status_level_2 = 'Interesado. Problema técnico'
    elif volver_a_llamar_flag:
        status_level_1 = 'Volver a llamar'
        # Usar el mapa de códigos si está disponible, sino usar valor por defecto
        if codigo_volver_llamar and codigo_volver_llamar in mapa_volver_llamar:
            status_level_2 = mapa_volver_llamar[codigo_volver_llamar]
        else:
            status_level_2 = 'no disponible cliente'  # Valor por defecto
    elif data.get('noInteresado') or codigo_no_interes in mapa_no_interes:
        status_level_1 = 'No Interesado'
        # Tomamos razón del mapa si existe, o texto libre proporcionado
        status_level_2 = mapa_no_interes.get(codigo_no_interes, data.get('razonNoInteres'))
    elif codigo_volver_llamar in mapa_volver_llamar:
        status_level_1 = 'Volver a llamar'
        status_level_2 = mapa_volver_llamar[codigo_volver_llamar]
    elif data.get('conPack'):
        status_level_1 = 'Cita Agendada'
        status_level_2 = 'Con Pack'

    # -------------------------------------------------------------
    # 3. Construcción de diccionario de actualización
    # -------------------------------------------------------------
    # Forzar strip en status levels si existen
    if status_level_1:
        status_level_1 = status_level_1.strip()
    if status_level_2:
        status_level_2 = status_level_2.strip()

    update_fields = {
        'status_level_1': status_level_1,
        'status_level_2': status_level_2,
        'conPack': data.get('conPack'),
        'hora_rellamada': data.get('horaRellamada'),
        'error_tecnico': data.get('errorTecnico'),
        'razon_vuelta_a_llamar': data.get('razonvueltaallamar'),
        'razon_no_interes': data.get('razonNoInteres'),
        'manual_management': data.get('gestionManual')
    }

    # -------------------------------------------------------------
    # 3.1. Manejo de preferencias de Pearl AI
    # -------------------------------------------------------------
    
    # Mapear preferenciaMT (MORNING/AFTERNOON) a preferencia_horario (mañana/tarde) 
    if preferencia_mt:
        if preferencia_mt.upper() == 'MORNING':
            update_fields['preferencia_horario'] = 'mañana'
        elif preferencia_mt.upper() == 'AFTERNOON':
            update_fields['preferencia_horario'] = 'tarde'
        logger.info(f"Preferencia de horario mapeada: {preferencia_mt} -> {update_fields.get('preferencia_horario')}")
    
    # Procesar preferenciaFecha si está presente
    if preferencia_fecha:
        try:
            # Validar y convertir formato de fecha
            if '/' in preferencia_fecha:
                # Formato DD/MM/YYYY
                dia, mes, anio = preferencia_fecha.split('/')
                fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            elif '-' in preferencia_fecha:
                # Detectar si es DD-MM-YYYY o YYYY-MM-DD
                parts = preferencia_fecha.split('-')
                if len(parts) == 3:
                    if len(parts[0]) == 4:
                        # Formato YYYY-MM-DD (ya válido)
                        fecha_formateada = preferencia_fecha
                    else:
                        # Formato DD-MM-YYYY
                        dia, mes, anio = parts
                        fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
                else:
                    raise ValueError(f"Formato de fecha no válido: {preferencia_fecha}")
            else:
                raise ValueError(f"Formato de fecha no reconocido: {preferencia_fecha}")
            
            update_fields['fecha_minima_reserva'] = fecha_formateada
            logger.info(f"Fecha de preferencia establecida: {preferencia_fecha} -> {fecha_formateada}")
            
        except Exception as e:
            logger.warning(f"Error procesando preferenciaFecha '{preferencia_fecha}': {e}")

    # -------------------------------------------------------------
    # 3.2. Manejo de parámetros de reservas automáticas
    # -------------------------------------------------------------
    # Procesar parámetros de reserva automática si están presentes
    if 'reservaAutomatica' in data:
        reserva_auto = data.get('reservaAutomatica')
        # Convertir a boolean si viene como string
        if isinstance(reserva_auto, str):
            reserva_auto = reserva_auto.lower() in ['true', '1', 'yes', 'si', 'sí']
        update_fields['reserva_automatica'] = bool(reserva_auto)
        
        # Si se marca para reserva automática, procesar preferencia y fecha
        if reserva_auto:
            # Preferencia de horario (por defecto 'mañana')
            preferencia = data.get('preferenciaHorario', 'mañana')
            if preferencia not in ['mañana', 'tarde']:
                preferencia = 'mañana'  # Valor por defecto si es inválido
            update_fields['preferencia_horario'] = preferencia
            
            # Fecha mínima para reserva (por defecto hoy + 15 días)
            fecha_minima = data.get('fechaMinimaReserva')
            if fecha_minima:
                try:
                    # Validar y convertir formato de fecha
                    if '/' in fecha_minima:
                        # Formato DD/MM/YYYY
                        dia, mes, anio = fecha_minima.split('/')
                        fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
                    elif '-' in fecha_minima:
                        # Detectar si es DD-MM-YYYY o YYYY-MM-DD
                        parts = fecha_minima.split('-')
                        if len(parts) == 3:
                            if len(parts[0]) == 4:
                                # Formato YYYY-MM-DD (ya válido)
                                fecha_formateada = fecha_minima
                            else:
                                # Formato DD-MM-YYYY
                                dia, mes, anio = parts
                                fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
                        else:
                            raise ValueError(f"Formato de fecha no válido: {fecha_minima}")
                    else:
                        # Asumir formato YYYY-MM-DD
                        fecha_formateada = fecha_minima
                    update_fields['fecha_minima_reserva'] = fecha_formateada
                except Exception as e:
                    logger.warning(f"Formato de fecha mínima inválido: {fecha_minima}. Usando fecha por defecto.")
                    # Usar fecha por defecto (hoy + 15 días)
                    from datetime import date, timedelta
                    fecha_defecto = date.today() + timedelta(days=15)
                    update_fields['fecha_minima_reserva'] = fecha_defecto.strftime('%Y-%m-%d')
            else:
                # Usar fecha por defecto (hoy + 15 días)
                from datetime import date, timedelta
                fecha_defecto = date.today() + timedelta(days=15)
                update_fields['fecha_minima_reserva'] = fecha_defecto.strftime('%Y-%m-%d')

    # Si llega una nueva cita, actualizamos los campos 'cita' (DATE) y opcionalmente 'hora_cita' (TIME)
    if data.get('nuevaCita'):
        try:
            # Intentar convertir el formato de fecha recibido (DD/MM/YYYY) a formato SQL (YYYY-MM-DD)
            fecha_str = data.get('nuevaCita')
            # Detectar el formato de la fecha recibida
            if '/' in fecha_str:
                # Formato DD/MM/YYYY
                dia, mes, anio = fecha_str.split('/')
                fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            else:
                # Asumir que ya viene en formato YYYY-MM-DD
                fecha_formateada = fecha_str
            
            # Guardar la fecha en la columna 'cita'
            update_fields['cita'] = fecha_formateada

            # Si también viene la hora de la cita, la guardamos en 'hora_cita'
            if data.get('horaCita'):
                hora_str = data.get('horaCita')
                # Asegurar formato HH:MM:SS
                if len(hora_str.split(':')) == 2:
                    hora_str += ':00'
                update_fields['hora_cita'] = hora_str

            # --- Ajustar automáticamente los status al recibir una cita ---
            update_fields['status_level_1'] = 'Cita Agendada'
            con_pack_val = data.get('conPack')
            if con_pack_val is not None:
                try:
                    truthy = str(con_pack_val).lower() in ['1', 'true', 'yes', 'si', 'sí', 'on']
                except Exception:
                    truthy = False
                update_fields['status_level_2'] = 'Con Pack' if truthy else 'Sin Pack'
        except Exception as e:
            logger.error(f"Error al procesar la fecha de cita: {e}")
            return jsonify({"error": f"Formato de fecha inválido: {data.get('nuevaCita')}. Use DD/MM/YYYY."}), 400

    # -------------------------------------------------------------
    # 4. Filtrar valores None para no sobreescribir con nulos
    # -------------------------------------------------------------

    # Filtrar campos que son None o cadenas vacías para no sobreescribir datos existentes
    update_data = {k: v for k, v in update_fields.items() if v is not None and v != ""}

    # Si no hay ningún otro dato aparte del teléfono, marcar como 'Volver a llamar - cortado'
    if not update_data:
        logger.info("Solo se proporcionó teléfono: marcando lead como 'Volver a llamar / cortado'.")
        update_data = {
            'status_level_1': 'Volver a llamar',
            'status_level_2': 'cortado'
        }

    # -------------------------------------------------------------
    # 5. Control de Intentos y Cierre Automático
    # -------------------------------------------------------------
    
    # Determinar si se debe incrementar intentos según parámetros existentes del JSON
    should_increment_attempts = False
    
    # ÚTILES POSITIVOS: NO incrementar intentos (llamada exitosa - cita conseguida)
    if data.get('nuevaCita') or data.get('conPack'):
        should_increment_attempts = False
        logger.info(f"Lead {telefono}: Útil positivo (cita conseguida) - NO se incrementan intentos")
        
    # ÚTILES NEGATIVOS: NO incrementar intentos (contacto exitoso, pero no acepta cita)
    elif data.get('noInteresado') or codigo_no_interes:
        should_increment_attempts = False
        logger.info(f"Lead {telefono}: Útil negativo (contacto exitoso, no acepta cita) - NO se incrementan intentos")
        
    # CASOS ESPECIALES QUE NO INCREMENTAN INTENTOS
    elif data.get('llamaraInteresado'):
        should_increment_attempts = False
        logger.info(f"Lead {telefono}: Llamará cuando esté interesado - NO se incrementan intentos")
        
    # CASOS QUE SÍ INCREMENTAN INTENTOS (no se logró contacto útil)
    elif data.get('volverALlamar') or buzon or data.get('errorTecnico'):
        should_increment_attempts = True
        logger.info(f"Lead {telefono}: Volver a llamar (no contacto útil) - SÍ se incrementan intentos")
        
    elif not update_data:  # Solo teléfono (llamada cortada)
        should_increment_attempts = True
        logger.info(f"Lead {telefono}: Solo teléfono (llamada cortada) - SÍ se incrementan intentos")
        
    else:
        # OTROS CASOS (legacy): Mantener lógica anterior
        should_increment_attempts = (
            update_data.get('status_level_1') == 'Volver a llamar' or 
            not update_data
        )
        logger.info(f"Lead {telefono}: Caso legacy - decisión: {'SÍ' if should_increment_attempts else 'NO'} incrementar intentos")
    
    # Conectar a la BD antes de usar
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    if should_increment_attempts:
        # Obtener configuración de máximo intentos desde scheduler_config
        try:
            cursor_temp = conn.cursor()
            cursor_temp.execute("SELECT config_value FROM scheduler_config WHERE config_key = 'max_attempts'")
            max_attempts_result = cursor_temp.fetchone()
            max_attempts = int(max_attempts_result[0]) if max_attempts_result else 6
            cursor_temp.close()
        except Exception as e:
            logger.warning(f"No se pudo obtener max_attempts de scheduler_config: {e}. Usando default: 6")
            max_attempts = 6
            
        # Obtener intentos actuales del lead
        try:
            cursor_temp = conn.cursor(dictionary=True)
            # Verificar si existe campo lead_status
            cursor_temp.execute("SHOW COLUMNS FROM leads LIKE 'lead_status'")
            has_lead_status = cursor_temp.fetchone() is not None
            
            if has_lead_status:
                cursor_temp.execute("SELECT call_attempts_count, lead_status FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 1", (telefono,))
            else:
                cursor_temp.execute("SELECT call_attempts_count FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 1", (telefono,))
            current_lead = cursor_temp.fetchone()
            cursor_temp.close()
            
            if current_lead:
                current_attempts = current_lead['call_attempts_count'] or 0
                new_attempts = current_attempts + 1
                
                # Incrementar contador de intentos
                update_data['call_attempts_count'] = new_attempts
                update_data['last_call_attempt'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Si alcanzó el máximo de intentos, cerrar el lead
                if new_attempts >= max_attempts:
                    logger.info(f"Lead {telefono} alcanzó máximo de intentos ({new_attempts}/{max_attempts}). Cerrando automáticamente.")
                    
                    # NUEVO: Asignar estado "No útil" al alcanzar máximo de intentos
                    update_data['status_level_1'] = 'No Interesado'
                    update_data['status_level_2'] = 'No útil'
                    
                    # Solo actualizar lead_status si existe el campo
                    if has_lead_status:
                        update_data['lead_status'] = 'closed'
                    
                    # Razón de cierre específica para máximo de intentos
                    closure_reason = 'No disponible (incluir cerrados por máximo de intentos)'
                        
                    # Solo actualizar closure_reason si existe el campo
                    try:
                        cursor_temp2 = conn.cursor()
                        cursor_temp2.execute("SHOW COLUMNS FROM leads LIKE 'closure_reason'")
                        has_closure_reason = cursor_temp2.fetchone() is not None
                        cursor_temp2.close()
                        if has_closure_reason:
                            update_data['closure_reason'] = closure_reason
                    except:
                        pass
                    
                    # Cambiar call_status para que no aparezca en listas de llamada
                    update_data['call_status'] = 'completed'
                    update_data['selected_for_calling'] = False
                    
                    logger.info(f"Lead {telefono} marcado como 'No útil' por máximo de intentos y cerrado con razón: {closure_reason}")
                else:
                    logger.info(f"Lead {telefono} marcado para reintento. Intentos: {new_attempts}/{max_attempts}")
                    # Asegurar que sigue abierto para futuros intentos si existe el campo
                    if has_lead_status:
                        update_data['lead_status'] = 'open'
            else:
                logger.warning(f"No se encontró lead con teléfono {telefono} para controlar intentos")
                
        except Exception as e:
            logger.error(f"Error controlando intentos para lead {telefono}: {e}")

    # Construir la consulta SQL dinámicamente
    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    sql_query = f"UPDATE leads SET {set_clause} WHERE telefono = %s"
    
    values = list(update_data.values())
    values.append(telefono)  # teléfono ya normalizado

    try:
        cursor = conn.cursor()
        cursor.execute(sql_query, tuple(values))

        if cursor.rowcount == 0:
            # Intentar de nuevo comparando solo los dígitos del teléfono completos
            logger.info("No hubo coincidencia exacta; probando coincidencia por todos los dígitos del número")
            sql_query_digits = f"UPDATE leads SET {set_clause} WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s"
            values_digits = list(update_data.values()) + [telefono]
            cursor.execute(sql_query_digits, tuple(values_digits))
            if cursor.rowcount == 0:
                # Puede que los valores enviados ya coincidan y por eso no se actualizó ninguna fila.
                cursor.execute("SELECT 1 FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 1", (telefono,))
                if cursor.fetchone():
                    logger.info(f"Lead {telefono} encontrado pero sin cambios a aplicar.")
                    return jsonify({"success": True, "message": "Lead encontrado. No había cambios que aplicar."})
                else:
                    logger.warning(f"No se encontró ningún lead con el teléfono: {telefono}")
                    return jsonify({"error": f"No se encontró ningún lead con el teléfono {telefono}"}), 404

        conn.commit()
        logger.info(f"Lead con teléfono {telefono} actualizado correctamente. {cursor.rowcount} fila(s) afectada(s).")

        # -------------------------------------------------------------
        # 6. Enviar notificación por email si se agendó una cita
        # -------------------------------------------------------------
        if (data.get('nuevaCita') or status_level_1 == 'Cita Agendada') and EMAIL_NOTIFICATIONS_AVAILABLE:
            try:
                # Obtener los datos del lead actualizado para la notificación
                cursor_email = conn.cursor()
                cursor_email.execute("""
                    SELECT nombre, apellidos, telefono, cita, hora_cita, preferencia_horario, 
                           nombre_clinica, conPack, status_level_1, status_level_2
                    FROM leads 
                    WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s 
                    LIMIT 1
                """, (telefono,))
                
                lead_data = cursor_email.fetchone()
                cursor_email.close()
                
                if lead_data:
                    # Crear diccionario con los datos del lead
                    lead_info = {
                        'nombre': lead_data[0],
                        'apellidos': lead_data[1], 
                        'telefono': lead_data[2],
                        'cita': lead_data[3],
                        'hora_cita': lead_data[4],
                        'preferencia_horario': lead_data[5],
                        'nombre_clinica': lead_data[6],
                        'conPack': lead_data[7],
                        'status_level_1': lead_data[8],
                        'status_level_2': lead_data[9]
                    }
                    
                    # Enviar notificación
                    email_sent = send_cita_notification(lead_info)
                    if email_sent:
                        logger.info(f"Notificación de cita enviada exitosamente para {telefono}")
                    else:
                        logger.warning(f"Error enviando notificación de cita para {telefono}")
                
            except Exception as e:
                logger.error(f"Error enviando notificación de cita para {telefono}: {e}")

        # -------------------------------------------------------------
        # 7. Integración con Call Scheduler para hora_rellamada
        # -------------------------------------------------------------
        hora_rellamada = data.get('horaRellamada')
        if hora_rellamada and SCHEDULER_AVAILABLE:
            try:
                # Obtener el ID del lead actualizado
                cursor_id = conn.cursor()
                cursor_id.execute("SELECT id FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 1", (telefono,))
                lead_result = cursor_id.fetchone()
                cursor_id.close()
                
                if lead_result:
                    lead_id = lead_result[0]
                    
                    # Procesar la fecha/hora de rellamada
                    scheduled_datetime = None
                    
                    # Intentar parsear diferentes formatos de fecha/hora
                    try:
                        # Formato 1: "DD/MM/YYYY HH:MM" o "DD/MM/YYYY HH:MM:SS"
                        if '/' in hora_rellamada and (' ' in hora_rellamada or ':' in hora_rellamada):
                            # Separar fecha y hora
                            if ' ' in hora_rellamada:
                                fecha_part, hora_part = hora_rellamada.split(' ', 1)
                            else:
                                # Solo fecha proporcionada, usar hora por defecto (10:00)
                                fecha_part = hora_rellamada
                                hora_part = '10:00'
                            
                            # Procesar fecha DD/MM/YYYY
                            dia, mes, anio = fecha_part.split('/')
                            fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
                            
                            # Procesar hora HH:MM o HH:MM:SS
                            if hora_part.count(':') == 1:
                                hora_part += ':00'
                            
                            # Crear datetime completo
                            scheduled_datetime = datetime.strptime(f"{fecha_formateada} {hora_part}", '%Y-%m-%d %H:%M:%S')
                        
                        # Formato 2: "YYYY-MM-DD HH:MM:SS" (formato SQL)
                        elif '-' in hora_rellamada and ':' in hora_rellamada:
                            scheduled_datetime = datetime.strptime(hora_rellamada, '%Y-%m-%d %H:%M:%S')
                        
                        # Formato 3: Solo fecha "DD/MM/YYYY" - usar hora por defecto
                        elif '/' in hora_rellamada:
                            dia, mes, anio = hora_rellamada.split('/')
                            fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
                            scheduled_datetime = datetime.strptime(f"{fecha_formateada} 10:00:00", '%Y-%m-%d %H:%M:%S')
                        
                        # Formato 4: Solo fecha "YYYY-MM-DD" - usar hora por defecto
                        elif '-' in hora_rellamada and hora_rellamada.count('-') == 2:
                            scheduled_datetime = datetime.strptime(f"{hora_rellamada} 10:00:00", '%Y-%m-%d %H:%M:%S')
                        
                    except ValueError as e:
                        logger.warning(f"No se pudo parsear hora_rellamada '{hora_rellamada}': {e}")
                    
                    # Si se pudo parsear la fecha/hora, programar la llamada
                    if scheduled_datetime:
                        # Verificar que la fecha sea futura
                        if scheduled_datetime > datetime.now():
                            # Insertar directamente en call_schedule
                            cursor_schedule = conn.cursor()
                            cursor_schedule.execute("""
                                INSERT INTO call_schedule 
                                (lead_id, scheduled_at, attempt_number, status, last_outcome, created_at, updated_at)
                                VALUES (%s, %s, %s, 'pending', 'callback_requested', NOW(), NOW())
                            """, (
                                lead_id, 
                                scheduled_datetime, 
                                (update_data.get('call_attempts_count', 0) or 0) + 1
                            ))
                            cursor_schedule.close()
                            conn.commit()
                            
                            logger.info(f"Lead {lead_id} programado para llamada de callback el {scheduled_datetime}")
                        else:
                            logger.warning(f"Fecha de callback {scheduled_datetime} está en el pasado, ignorando")
                    
                else:
                    logger.warning(f"No se pudo obtener ID del lead con teléfono {telefono} para programar callback")
                    
            except Exception as e:
                logger.error(f"Error integrando con scheduler para callback: {e}")
                # No fallar la actualización principal por error en scheduling
        
        elif hora_rellamada and not SCHEDULER_AVAILABLE:
            logger.warning(f"hora_rellamada proporcionada pero CallScheduler no está disponible")

        return jsonify({
            "success": True,
            "message": f"Lead {telefono} actualizado correctamente."
        })

    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos al actualizar el lead {telefono}: {err}")
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@resultado_api.route('/api/leads_reserva_automatica', methods=['GET'])
def obtener_leads_reserva_automatica():
    """
    Obtener leads marcados para reserva automática
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT id, nombre, apellidos, telefono, area_id, 
               preferencia_horario, fecha_minima_reserva,
               codigo_postal, ciudad, status_level_1, status_level_2
        FROM leads 
        WHERE reserva_automatica = TRUE
        ORDER BY fecha_minima_reserva ASC, id ASC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convertir date a string para JSON
        for row in results:
            if row.get('fecha_minima_reserva'):
                row['fecha_minima_reserva'] = row['fecha_minima_reserva'].strftime("%Y-%m-%d")
        
        return jsonify({
            "success": True,
            "count": len(results),
            "leads": results
        })
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@resultado_api.route('/api/obtener_resultados', methods=['GET'])
def obtener_resultados():
    """
    Obtener contactos filtrados por resultado de llamada
    """
    # Parámetro opcional de filtrado
    resultado = request.args.get('resultado')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, nombre, apellidos, telefono, cita, conPack, resultado_llamada FROM leads WHERE 1=1"
        params = []
        
        if resultado:
            query += " AND resultado_llamada = %s"
            params.append(resultado)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convertir datetime a string para JSON
        for row in results:
            if row.get('cita'):
                row['cita'] = row['cita'].strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "success": True,
            "count": len(results),
            "contactos": results
        })
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@resultado_api.route('/api/marcar_reserva_automatica', methods=['POST'])
def marcar_reserva_automatica():
    """
    Marca o desmarca un lead para reserva automática por el daemon.
    
    Body JSON:
        {
            "telefono": "+34600000000",  // Teléfono del lead (requerido)
            "reserva_automatica": true,  // true = daemon procesa, false = no procesa
            "preferencia_horario": "mañana",  // opcional: "mañana" o "tarde"
            "fecha_minima_reserva": "2025-08-15"  // opcional: formato YYYY-MM-DD
        }
    
    Returns:
        JSON: Resultado de la operación
    """
    try:
        data = request.get_json() or {}
        
        # Validar parámetros requeridos
        telefono_raw = data.get('telefono')
        if not telefono_raw:
            return jsonify({
                "success": False,
                "error": "Se requiere el número de teléfono"
            }), 400
        
        # Normalizar teléfono (igual que en actualizar_resultado)
        import re
        telefono_raw = str(telefono_raw)
        telefono_digits = re.sub(r'\D', '', telefono_raw)
        if len(telefono_digits) > 9:
            telefono_digits = telefono_digits[-9:]
        telefono = telefono_digits

        reserva_automatica = data.get('reserva_automatica', True)
        if not isinstance(reserva_automatica, bool):
            return jsonify({
                "success": False,
                "error": "reserva_automatica debe ser true o false"
            }), 400
        
        # Parámetros opcionales
        preferencia_horario = data.get('preferencia_horario', 'mañana')
        if preferencia_horario not in ['mañana', 'tarde']:
            preferencia_horario = 'mañana'
        
        fecha_minima_reserva = data.get('fecha_minima_reserva')
        
        # Conectar a la base de datos
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "success": False,
                "error": "Error de conexión a la base de datos"
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Buscar el lead por teléfono
            cursor.execute("""
                SELECT id, nombre, apellidos 
                FROM leads 
                WHERE telefono = %s OR telefono2 = %s
                LIMIT 1
            """, (telefono, telefono))
            
            lead = cursor.fetchone()
            if not lead:
                return jsonify({
                    "success": False,
                    "error": f"No se encontró ningún lead con teléfono {telefono_raw}"
                }), 404
            
            lead_id = lead[0]
            lead_nombre = f"{lead[1] or ''} {lead[2] or ''}".strip()
            
            # Construir la consulta de actualización
            if reserva_automatica:
                # Marcar para reserva automática con parámetros opcionales
                update_query = """
                UPDATE leads 
                SET reserva_automatica = TRUE,
                    manual_management = FALSE,
                    preferencia_horario = %s
                """
                params = [preferencia_horario]
                
                # Añadir fecha mínima si se proporciona
                if fecha_minima_reserva:
                    update_query += ", fecha_minima_reserva = %s"
                    params.append(fecha_minima_reserva)
                
                update_query += " WHERE id = %s"
                params.append(lead_id)
            else:
                # Desmarcar para reserva automática
                update_query = """
                UPDATE leads 
                SET reserva_automatica = FALSE
                WHERE id = %s
                """
                params = [lead_id]
            
            # Ejecutar la actualización
            cursor.execute(update_query, params)
            updated_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Lead {lead_id} ({telefono}) marcado para reserva_automatica = {reserva_automatica}")
            
            return jsonify({
                "success": True,
                "message": f"Lead {lead_nombre} actualizado correctamente",
                "lead_id": lead_id,
                "telefono": telefono_raw,
                "nombre": lead_nombre,
                "reserva_automatica": reserva_automatica,
                "preferencia_horario": preferencia_horario if reserva_automatica else None,
                "fecha_minima_reserva": fecha_minima_reserva if reserva_automatica else None,
                "timestamp": datetime.now().isoformat()
            })
            
        except mysql.connector.Error as err:
            logger.error(f"Error actualizando reserva automática: {err}")
            return jsonify({
                "success": False,
                "error": f"Error de base de datos: {str(err)}"
            }), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
        
    except Exception as e:
        logger.error(f"Error en marcar_reserva_automatica: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500



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

# El logger será configurado por la aplicación principal
logger = logging.getLogger(__name__)

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

    # Mapas de traducción de códigos compactos → descripciones
    mapa_no_interes = {
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

    # -------------------------------------------------------------
    # 2. Deducción automática de status_level_1 y status_level_2
    # -------------------------------------------------------------
    status_level_1 = None
    status_level_2 = None

    if data.get('nuevaCita'):
        # Una nueva cita siempre se considera un Éxito
        status_level_1 = 'Éxito'
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
        status_level_1 = 'Éxito'
        status_level_2 = 'Contratado'
    elif data.get('errorTecnico'):
        status_level_1 = 'Volver a llamar'
        status_level_2 = 'Interesado. Problema técnico'

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
    # 3.1. Manejo de parámetros de reservas automáticas
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

    # Construir la consulta SQL dinámicamente
    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    sql_query = f"UPDATE leads SET {set_clause} WHERE telefono = %s"
    
    values = list(update_data.values())
    values.append(telefono)  # teléfono ya normalizado

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500

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



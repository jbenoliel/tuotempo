#!/usr/bin/env python3
"""
Procesador de Reservas Automáticas
==================================

Este script busca leads marcados para reserva automática y realiza las reservas
según sus preferencias de horario y fecha mínima.

Funcionalidades:
- Busca leads con reserva_automatica = True
- Filtra por fecha_minima_reserva >= fecha actual
- Consulta disponibilidad según preferencia_horario
- Realiza la reserva automáticamente
- Actualiza el estado del lead

Uso:
    python procesador_reservas_automaticas.py
    
    # O como proceso periódico (cada 30 minutos)
    python procesador_reservas_automaticas.py --daemon --interval 30
"""

import mysql.connector
import logging
import os
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import settings
from tuotempo import Tuotempo
from daemon_monitor import daemon_monitor, initialize_daemon_monitor

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reservas_automaticas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProcesadorReservasAutomaticas:
    """Clase principal para procesar reservas automáticas"""
    
    def __init__(self, intervalo_minutos=30):
        self.intervalo_minutos = intervalo_minutos
        self.daemon_activo = False
        self.hilo_daemon = None
        self.logger = logging.getLogger(__name__)
        
        # Inicializar sistema de monitoreo
        initialize_daemon_monitor()

    # Configuración de la base de datos
    DB_CONFIG = {
        'host': settings.DB_HOST,
        'port': settings.DB_PORT,
        'user': settings.DB_USER,
        'password': settings.DB_PASSWORD,
        'database': settings.DB_DATABASE,
        'ssl_disabled': True,
        'autocommit': True,
        'charset': 'utf8mb4',
        'use_unicode': True
    }

    def get_db_connection(self):
        """Establece conexión con la base de datos MySQL"""
        try:
            connection = mysql.connector.connect(**self.DB_CONFIG)
            return connection
        except mysql.connector.Error as err:
            logger.error(f"Error conectando a MySQL: {err}")
            # Si falla con SSL, intentar sin SSL
            if 'SSL' in str(err) or '2026' in str(err):
                try:
                    logger.info("Intentando conexión sin SSL...")
                    config_no_ssl = self.DB_CONFIG.copy()
                    config_no_ssl['ssl_disabled'] = True
                    connection = mysql.connector.connect(**config_no_ssl)
                    return connection
                except mysql.connector.Error as err2:
                    logger.error(f"Error conectando sin SSL: {err2}")
            return None
    
    def procesar_leads_automaticos(self):
        """Procesa todos los leads marcados para reserva automática"""
        cycle_start_time = datetime.now()
        self.logger.info("[RESERVAS-DAEMON] --- Iniciando ciclo: {} ---".format(
            cycle_start_time.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Registrar inicio del ciclo en el monitor
        daemon_monitor.start_cycle()
        
        leads_procesados = 0
        reservas_exitosas = 0
        reservas_fallidas = 0
        
        # Obtener leads elegibles
        conn = self.get_db_connection()
        if not conn:
            error_msg = "No se pudo conectar a la base de datos"
            self.logger.error(error_msg)
            daemon_monitor.log_error(error_msg)
            return
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Consulta para obtener TODOS los leads marcados para reserva automática
            query = """
            SELECT id, nombre, apellidos, telefono, area_id, 
                   preferencia_horario, fecha_minima_reserva,
                   codigo_postal, ciudad
            FROM leads 
            WHERE reserva_automatica = TRUE 
              AND cita IS NULL
              AND status_level_1 NOT IN ('Cita Agendada', 'No interesado')
            ORDER BY 
              CASE WHEN fecha_minima_reserva IS NULL THEN 0 ELSE 1 END,
              fecha_minima_reserva ASC, 
              id ASC
            LIMIT 100
            """
            
            cursor.execute(query)
            leads = cursor.fetchall()
            
            if not leads:
                self.logger.info("No se encontraron leads marcados para reserva automática")
                # Registrar ciclo completado sin leads
                daemon_monitor.end_cycle(0, 0, 0)
                return
            
            leads_procesados = len(leads)
            self.logger.info(f"Encontrados {leads_procesados} leads marcados para reserva automática")
            
            for lead in leads:
                try:
                    self.logger.info(f"Procesando lead {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                    
                    # Determinar fecha desde la cual buscar slots
                    # Si no hay fecha mínima, usar fecha actual + 15 días
                    if lead['fecha_minima_reserva']:
                        fecha_desde = lead['fecha_minima_reserva']
                    else:
                        fecha_desde = date.today() + timedelta(days=15)
                    
                    # Consultar disponibilidad
                    tuotempo = Tuotempo()
                    slots = tuotempo.get_available_slots(
                        locations_lid=[lead['area_id']], 
                        start_date=fecha_desde.strftime('%d-%m-%Y'), 
                        days=14
                    )
                    
                    if slots and len(slots) > 0:
                        # Tomar el primer slot disponible
                        slot_seleccionado = slots[0]
                        
                        # Realizar la reserva
                        if self.realizar_reserva(lead, slot_seleccionado):
                            reservas_exitosas += 1
                            self.logger.info(f"Reserva realizada exitosamente para lead {lead['id']}")
                        else:
                            reservas_fallidas += 1
                            error_msg = f"No se pudo realizar la reserva para lead {lead['id']}"
                            self.logger.warning(error_msg)
                            daemon_monitor.log_error(error_msg)
                    else:
                        reservas_fallidas += 1
                    
                    # Pausa entre reservas para no sobrecargar la API
                    time.sleep(2)
                    
                except Exception as e:
                    reservas_fallidas += 1
                    error_msg = f"Error procesando lead {lead.get('id', 'unknown')}: {e}"
                    self.logger.error(error_msg)
                    daemon_monitor.log_error(error_msg)
            
            # Registrar fin del ciclo en el monitor
            daemon_monitor.end_cycle(leads_procesados, reservas_exitosas, reservas_fallidas)
            
            # Calcular duración del ciclo
            fin_ciclo = datetime.now()
            duracion = (fin_ciclo - cycle_start_time).total_seconds()
            self.logger.info("[RESERVAS-DAEMON] --- Ciclo completado en {:.2f} segundos ---".format(duracion))
        
        except mysql.connector.Error as err:
            error_msg = f"Error de base de datos: {err}"
            self.logger.error(error_msg)
            daemon_monitor.log_error(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            self.logger.error(error_msg)
            daemon_monitor.log_error(error_msg)
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def realizar_reserva(self, lead, slot):
        """Realiza la reserva para un lead específico"""
        try:
            tuotempo = Tuotempo()
            
            # Preparar datos del usuario
            user_info = {
                'name': lead['nombre'] or '',
                'surname': lead['apellidos'] or '',
                'birth_date': '',  # No tenemos fecha de nacimiento en el lead
                'mobile_phone': lead['telefono']
            }
            
            # Preparar datos de disponibilidad (normalizar claves)
            availability = {
                'start_date': slot.get('start_date'),
                'startTime': slot.get('startTime'),
                'endTime': slot.get('endTime'),
                'resourceid': slot.get('resourceid') or slot.get('resourceId'),
                'activityid': slot.get('activityid') or slot.get('activityId') or os.getenv('TUOTEMPO_ACTIVITY_ID', 'sc159232371eb9c1')
            }
            
            # Verificar que tenemos los datos necesarios
            required_fields = ['start_date', 'startTime', 'endTime', 'resourceid', 'activityid']
            missing_fields = [field for field in required_fields if not availability.get(field)]
            
            if missing_fields:
                logger.error(f"Faltan campos requeridos para la reserva: {missing_fields}")
                logger.error(f"Slot recibido: {slot}")
                return False
            
            logger.info(f"Datos de reserva - Usuario: {user_info}, Disponibilidad: {availability}")
            
            # Realizar la reserva usando el método create_reservation
            response = tuotempo.create_reservation(user_info=user_info, availability=availability)
            
            logger.info(f"Respuesta de reserva TuoTempo: {response}")
            
            if response.get('result') == 'OK':
                # Actualizar el lead con la información de la cita
                fecha_cita = slot.get('start_date')
                hora_cita = slot.get('startTime')
                
                self.actualizar_lead_con_cita(
                    lead['id'], 
                    fecha_cita, 
                    hora_cita,
                    response
                )
                
                logger.info(f"Reserva realizada exitosamente para lead {lead['id']} - {lead['nombre']} {lead['apellidos']}")
                return True
            else:
                logger.error(f"Error en la respuesta de TuoTempo para lead {lead['id']}: {response}")
                return False
                
        except ImportError as e:
            logger.error(f"No se pudo importar la clase TuoTempo: {e}")
            return False
        except Exception as e:
            logger.error(f"Error al realizar reserva para lead {lead['id']}: {e}")
            return False
    
    def actualizar_lead_con_cita(self, lead_id, fecha_cita, hora_cita, reserva_response):
        """Actualiza el lead con la información de la cita programada"""
        conn = self.get_db_connection()
        if not conn:
            error_msg = "No se pudo conectar a la base de datos para actualizar lead"
            self.logger.error(error_msg)
            daemon_monitor.log_error(error_msg)
            return
        
        try:
            cursor = conn.cursor()
            
            # Actualizar el lead con la información de la cita
            update_query = """
            UPDATE leads 
            SET cita = %s, 
                hora_cita = %s,
                status_level_1 = 'Cita Agendada',
                status_level_2 = 'Reserva Automática',
                reserva_automatica = FALSE,
                updated_at = NOW()
            WHERE id = %s
            """
            
            cursor.execute(update_query, (fecha_cita, hora_cita, lead_id))
            conn.commit()
            
            logger.info(f"Lead {lead_id} actualizado con cita: {fecha_cita} {hora_cita}")
            
        except mysql.connector.Error as err:
            error_msg = f"Error de base de datos: {err}"
            self.logger.error(error_msg)
            daemon_monitor.log_error(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            self.logger.error(error_msg)
            daemon_monitor.log_error(error_msg)
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def detener_daemon(self):
        """Detiene el daemon de procesamiento de reservas automáticas"""
        if not self.daemon_activo:
            self.logger.warning("El daemon no está activo")
            return
        
        self.daemon_activo = False
        if self.hilo_daemon:
            self.hilo_daemon.join(timeout=5)
        
        # Marcar daemon como detenido en el monitor
        daemon_monitor.mark_daemon_stopped()
        
        self.logger.info("[RESERVAS-DAEMON] Daemon detenido")
    
    def iniciar_daemon(self):
        """Inicia el daemon de procesamiento de reservas automáticas"""
        if self.daemon_activo:
            self.logger.warning("El daemon ya está activo")
            return
        
        self.daemon_activo = True
        self.hilo_daemon = threading.Thread(target=self._ejecutar_daemon, daemon=True)
        self.hilo_daemon.start()
        
        # Actualizar estado en el monitor
        daemon_monitor.update_heartbeat()
        
        self.logger.info(f"[RESERVAS-DAEMON] Daemon iniciado con intervalo de {self.intervalo_minutos} minutos")
    
    def _ejecutar_daemon(self):
        """Ejecuta el daemon de procesamiento de reservas automáticas"""
        while self.daemon_activo:
            try:
                self.procesar_leads_automaticos()
                self.logger.info(f"[RESERVAS-DAEMON] Esperando {self.intervalo_minutos} minutos hasta el próximo procesamiento...")
                time.sleep(self.intervalo_minutos * 60)  # Convertir minutos a segundos
            except KeyboardInterrupt:
                self.logger.info("Deteniendo daemon por interrupción del usuario")
                break
            except Exception as e:
                self.logger.error(f"[RESERVAS-DAEMON] Error en el daemon: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de reintentar

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Procesador de Reservas Automáticas')
    parser.add_argument('--daemon', action='store_true', help='Ejecutar como daemon periódico')
    parser.add_argument('--interval', type=int, default=30, help='Intervalo en minutos (solo con --daemon)')
    
    args = parser.parse_args()
    
    procesador = ProcesadorReservasAutomaticas(intervalo_minutos=args.interval)
    
    if args.daemon:
        logger.info(f"Iniciando modo daemon con intervalo de {args.interval} minutos")
        
        procesador.iniciar_daemon()
        
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Deteniendo daemon por interrupción del usuario")
                procesador.detener_daemon()
                break
                time.sleep(60)  # Esperar 1 minuto antes de reintentar
    else:
        # Ejecutar una sola vez
        procesador.procesar_reservas_automaticas()

if __name__ == "__main__":
    main()

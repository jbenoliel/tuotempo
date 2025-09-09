#!/usr/bin/env python3
"""
Daemon local para envío de emails de citas agendadas
Monitorea la BD cada minuto y envía emails para nuevas citas
"""

import time
import logging
from datetime import datetime, timedelta
import pymysql
from config import settings
from email_notifications import send_cita_notification

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailCitasDaemon:
    """Daemon para envío automático de emails de citas"""
    
    def __init__(self):
        self.running = False
        self.last_check = None
        
    def get_db_connection(self):
        """Crear conexión a la base de datos"""
        try:
            connection = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_DATABASE,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except Exception as e:
            logger.error(f"Error conectando a BD: {e}")
            return None
    
    def get_new_citas(self):
        """Obtener citas nuevas desde la última verificación"""
        connection = self.get_db_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor()
            
            # Si es la primera vez, buscar citas de las últimas 24 horas
            if self.last_check is None:
                time_threshold = datetime.now() - timedelta(hours=24)
                logger.info("Primera ejecución: buscando citas de las últimas 24 horas")
            else:
                time_threshold = self.last_check
                logger.info(f"Buscando citas desde: {time_threshold}")
            
            query = """
                SELECT 
                    id,
                    nombre,
                    apellidos,
                    telefono,
                    email,
                    cita,
                    hora_cita,
                    nombre_clinica,
                    direccion_clinica,
                    status_level_1,
                    status_level_2,
                    conPack,
                    updated_at
                FROM leads 
                WHERE status_level_1 = 'Cita Agendada'
                  AND updated_at > %s
                ORDER BY updated_at ASC
            """
            
            cursor.execute(query, (time_threshold,))
            results = cursor.fetchall()
            
            logger.info(f"Encontradas {len(results)} nuevas citas")
            return results
            
        except Exception as e:
            logger.error(f"Error consultando nuevas citas: {e}")
            return []
        finally:
            connection.close()
    
    def mark_email_sent(self, lead_id):
        """Marcar que el email fue enviado (opcional: crear campo email_sent)"""
        # Por ahora solo loguear, más adelante podríamos añadir un campo email_sent
        logger.info(f"Email enviado para lead ID: {lead_id}")
    
    def process_new_citas(self):
        """Procesar y enviar emails para nuevas citas"""
        citas = self.get_new_citas()
        
        emails_sent = 0
        for cita in citas:
            try:
                # Preparar datos para el email
                lead_data = {
                    'id': cita['id'],
                    'nombre': cita['nombre'],
                    'apellidos': cita['apellidos'],
                    'telefono': cita['telefono'],
                    'email': cita['email'],
                    'cita': cita['cita'],
                    'hora_cita': cita['hora_cita'],
                    'nombre_clinica': cita['nombre_clinica'],
                    'direccion_clinica': cita['direccion_clinica'],
                    'conPack': bool(cita['conPack']),
                    'status_level_1': cita['status_level_1'],
                    'status_level_2': cita['status_level_2'],
                    'preferencia_horario': 'Mañana' if cita['status_level_2'] and 'mañana' in cita['status_level_2'].lower() else 'No especificada'
                }
                
                # Enviar email
                if send_cita_notification(lead_data):
                    emails_sent += 1
                    self.mark_email_sent(cita['id'])
                    logger.info(f"✅ Email enviado para {cita['nombre']} {cita['apellidos']} - Tel: {cita['telefono']}")
                else:
                    logger.warning(f"❌ Error enviando email para {cita['nombre']} {cita['apellidos']} - Tel: {cita['telefono']}")
                    
                # Pequeña pausa entre emails
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error procesando cita ID {cita['id']}: {e}")
        
        if emails_sent > 0:
            logger.info(f"📧 Total emails enviados: {emails_sent}")
        
        # Actualizar timestamp de última verificación
        self.last_check = datetime.now()
    
    def run(self):
        """Ejecutar daemon en bucle"""
        logger.info("🚀 Iniciando Email Citas Daemon")
        logger.info(f"📧 Configuración: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}")
        
        self.running = True
        
        try:
            while self.running:
                logger.info("🔍 Verificando nuevas citas...")
                self.process_new_citas()
                
                # Esperar 60 segundos antes de la siguiente verificación
                logger.info("💤 Esperando 60 segundos hasta próxima verificación...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("🛑 Daemon detenido por el usuario")
        except Exception as e:
            logger.error(f"💥 Error en daemon: {e}")
        finally:
            self.running = False
            logger.info("🔚 Email Citas Daemon finalizado")
    
    def stop(self):
        """Detener daemon"""
        logger.info("🛑 Solicitando parada del daemon...")
        self.running = False

def main():
    """Función principal"""
    daemon = EmailCitasDaemon()
    
    try:
        daemon.run()
    except Exception as e:
        logger.error(f"Error ejecutando daemon: {e}")

if __name__ == "__main__":
    main()
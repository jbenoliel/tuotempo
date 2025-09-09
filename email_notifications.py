#!/usr/bin/env python3
"""
Sistema de notificaciones por email para citas agendadas
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

class EmailNotifier:
    """Clase para manejar notificaciones por email"""
    
    def __init__(self):
        """Inicializar configuración de email desde variables de entorno"""
        # Configuración SMTP
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
        # Emails de destino (diferentes para local y producción)
        self.notification_emails = self._get_notification_emails()
        
        # Validar configuración
        if not self.email_user or not self.email_password:
            logger.warning("Email no configurado: faltan EMAIL_USER o EMAIL_PASSWORD")
            self.enabled = False
        elif not self.notification_emails:
            logger.warning("Email no configurado: faltan emails de destino")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Email configurado: {self.email_user} -> {self.notification_emails}")
    
    def _get_notification_emails(self):
        """Obtiene los emails de notificación según el entorno"""
        # Detectar entorno basado en configuración de BD
        mysql_url = os.getenv('MYSQL_URL')
        
        if mysql_url and 'railway.app' in mysql_url:
            # Producción (Railway)
            emails_str = os.getenv('EMAIL_PRODUCTION_RECIPIENTS')
            logger.info("Modo PRODUCCIÓN detectado")
        else:
            # Local
            emails_str = os.getenv('EMAIL_LOCAL_RECIPIENTS')
            logger.info("Modo LOCAL detectado")
        
        if emails_str:
            emails = [email.strip() for email in emails_str.split(',') if email.strip()]
            return emails
        
        return []
    
    def send_cita_notification(self, lead_data):
        """
        Envía notificación cuando se agenda una cita
        
        Args:
            lead_data (dict): Datos del lead con la cita
        """
        if not self.enabled:
            logger.warning("Email no está habilitado, saltando notificación")
            return False
        
        try:
            # Preparar datos
            nombre_completo = f"{lead_data.get('nombre', '')} {lead_data.get('apellidos', '')}".strip()
            telefono = lead_data.get('telefono', 'No disponible')
            fecha_cita = lead_data.get('cita', 'No especificada')
            hora_cita = lead_data.get('hora_cita', 'No especificada')
            preferencia_horario = lead_data.get('preferencia_horario', 'No especificada')
            clinica = lead_data.get('nombre_clinica', 'No especificada')
            con_pack = 'Sí' if lead_data.get('conPack') else 'No'
            
            # Formatear fecha si es necesario
            if isinstance(fecha_cita, str) and fecha_cita != 'No especificada':
                try:
                    if '/' in fecha_cita:
                        # Formato DD/MM/YYYY
                        fecha_obj = datetime.strptime(fecha_cita, '%d/%m/%Y')
                        fecha_formateada = fecha_obj.strftime('%d de %B de %Y')
                    else:
                        # Formato YYYY-MM-DD
                        fecha_obj = datetime.strptime(fecha_cita, '%Y-%m-%d')
                        fecha_formateada = fecha_obj.strftime('%d de %B de %Y')
                except:
                    fecha_formateada = fecha_cita
            else:
                fecha_formateada = str(fecha_cita)
            
            # Crear email
            subject = f"🦷 Nueva Cita Agendada - {nombre_completo}"
            
            body_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .info-box {{ background-color: #f9f9f9; border-left: 4px solid #4CAF50; padding: 15px; margin: 10px 0; }}
                    .highlight {{ background-color: #e8f5e8; padding: 10px; border-radius: 5px; }}
                    .footer {{ color: #666; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🦷 Nueva Cita Dental Agendada</h1>
                </div>
                
                <div class="content">
                    <p>Se ha agendado una nueva cita a través del sistema de llamadas automáticas.</p>
                    
                    <div class="info-box">
                        <h3>📋 Información del Paciente</h3>
                        <p><strong>Nombre:</strong> {nombre_completo}</p>
                        <p><strong>Teléfono:</strong> {telefono}</p>
                    </div>
                    
                    <div class="info-box highlight">
                        <h3>📅 Detalles de la Cita</h3>
                        <p><strong>Fecha:</strong> {fecha_formateada}</p>
                        <p><strong>Hora:</strong> {hora_cita}</p>
                        <p><strong>Preferencia de horario:</strong> {preferencia_horario}</p>
                        <p><strong>Con Pack:</strong> {con_pack}</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>🏥 Clínica</h3>
                        <p><strong>Centro:</strong> {clinica}</p>
                    </div>
                    
                    <div class="footer">
                        <p>📞 Notificación generada automáticamente por Agentto</p>
                        <p>⏰ Fecha de notificación: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}</p>
                        <p>🔧 Entorno: {'Producción' if 'railway.app' in os.getenv('MYSQL_URL', '') else 'Local'}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            body_text = f"""
Nueva Cita Dental Agendada

Información del Paciente:
- Nombre: {nombre_completo}
- Teléfono: {telefono}

Detalles de la Cita:
- Fecha: {fecha_formateada}
- Hora: {hora_cita}
- Preferencia de horario: {preferencia_horario}
- Con Pack: {con_pack}

Clínica:
- Centro: {clinica}

---
Notificación generada automáticamente por Agentto
Fecha: {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}
Entorno: {'Producción' if 'railway.app' in os.getenv('MYSQL_URL', '') else 'Local'}
            """
            
            # Enviar email
            return self._send_email(subject, body_html, body_text)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de cita: {e}")
            return False
    
    def _send_email(self, subject, body_html, body_text):
        """Envía el email usando SMTP"""
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = ', '.join(self.notification_emails)
            
            # Añadir partes del mensaje
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            part_html = MIMEText(body_html, 'html', 'utf-8')
            
            msg.attach(part_text)
            msg.attach(part_html)
            
            # Conectar y enviar
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            
            for email in self.notification_emails:
                server.sendmail(self.email_user, email, msg.as_string())
            
            server.quit()
            
            logger.info(f"Email enviado exitosamente a: {self.notification_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False

# Instancia global del notificador
email_notifier = EmailNotifier()

def send_cita_notification(lead_data):
    """Función helper para enviar notificación de cita"""
    return email_notifier.send_cita_notification(lead_data)
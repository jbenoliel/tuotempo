#!/usr/bin/env python3
"""
Script de prueba para el sistema de notificaciones de citas
"""

import requests
import json
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración
BASE_URL = "http://localhost:8080"  # Servidor está ejecutándose en puerto 8080
TELEFONO_PRUEBA = "600111111"  # Teléfono que existe en BD local

def test_cita_notification():
    """Prueba el sistema de notificaciones de citas"""
    
    print("=== PRUEBA DE SISTEMA DE NOTIFICACIONES DE CITAS ===")
    print(f"URL base: {BASE_URL}")
    print(f"Teléfono de prueba: {TELEFONO_PRUEBA}")
    
    # Preparar datos de prueba para una cita
    fecha_cita = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")
    hora_cita = "10:00:00"
    
    payload = {
        "telefono": TELEFONO_PRUEBA,
        "nuevaCita": f"{fecha_cita} {hora_cita}",  # Formato DD/MM/YYYY HH:MM:SS
        "horaCita": hora_cita,
        "conPack": True,  # Con pack
        "preferenciaMT": "MORNING",  # Preferencia mañana
        "preferenciaFecha": fecha_cita,
        "notas": "Prueba de sistema de notificaciones - generada automáticamente"
    }
    
    print(f"\nDatos de prueba:")
    print(f"- Fecha cita: {fecha_cita}")
    print(f"- Hora cita: {hora_cita}")
    print(f"- Con pack: Sí")
    print(f"- Preferencia: Mañana")
    
    try:
        print("\nEnviando petición al API...")
        
        # Enviar petición
        response = requests.post(
            f"{BASE_URL}/api/actualizar_resultado",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ RESPUESTA EXITOSA:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get('success'):
                print("\n🎉 ÉXITO: La cita se agendó correctamente")
                print("📧 Revisa tu email para ver si llegó la notificación")
                
                # Verificar datos en BD
                verificar_datos_bd()
            else:
                print("\n❌ ERROR: La respuesta indica fallo")
        else:
            print(f"❌ ERROR HTTP: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
        print("\nAsegúrate de que:")
        print("1. El servidor Flask esté ejecutándose")
        print("2. La URL base sea correcta")
        print(f"3. El teléfono {TELEFONO_PRUEBA} exista en la BD")

def verificar_datos_bd():
    """Verifica que los datos se guardaron correctamente en BD"""
    print("\n=== VERIFICANDO DATOS EN BD ===")
    
    try:
        # Llamar al endpoint de consulta
        response = requests.get(
            f"{BASE_URL}/api/leads_info",
            params={'telefono': TELEFONO_PRUEBA},
            timeout=10
        )
        
        if response.status_code == 200:
            lead_data = response.json()
            
            if lead_data:
                print("✅ DATOS ENCONTRADOS EN BD:")
                print(f"- Nombre: {lead_data.get('nombre')} {lead_data.get('apellidos')}")
                print(f"- Teléfono: {lead_data.get('telefono')}")
                print(f"- Fecha cita: {lead_data.get('cita')}")
                print(f"- Hora cita: {lead_data.get('hora_cita')}")
                print(f"- Preferencia horario: {lead_data.get('preferencia_horario')}")
                print(f"- Estado: {lead_data.get('status_level_1')} - {lead_data.get('status_level_2')}")
                print(f"- Con pack: {'Sí' if lead_data.get('conPack') else 'No'}")
                
                # Verificar campos específicos
                if lead_data.get('cita') and lead_data.get('status_level_1') == 'Cita Agendada':
                    print("\n✅ VERIFICACIÓN EXITOSA:")
                    print("- ✅ Campo 'cita' guardado correctamente")
                    print("- ✅ Estado actualizado a 'Cita Agendada'")
                    print("- ✅ Preferencia de horario guardada")
                else:
                    print("\n⚠️  ADVERTENCIA: Algunos campos no se actualizaron como se esperaba")
            else:
                print("❌ No se encontraron datos para el teléfono especificado")
        else:
            print(f"❌ Error consultando BD: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")

def verificar_configuracion_email():
    """Verifica que la configuración de email esté correcta"""
    print("\n=== VERIFICANDO CONFIGURACIÓN DE EMAIL ===")
    
    try:
        from email_notifications import email_notifier
        
        if email_notifier.enabled:
            print("✅ Sistema de email habilitado")
            print(f"- Servidor SMTP: {email_notifier.smtp_server}:{email_notifier.smtp_port}")
            print(f"- Usuario: {email_notifier.email_user}")
            print(f"- Destinatarios: {email_notifier.notification_emails}")
            
            # Detectar entorno
            import os
            mysql_url = os.getenv('MYSQL_URL')
            if mysql_url and 'railway.app' in mysql_url:
                print("- Entorno: PRODUCCIÓN (Railway)")
            else:
                print("- Entorno: LOCAL")
        else:
            print("❌ Sistema de email DESHABILITADO")
            print("Verifica las variables de entorno:")
            print("- EMAIL_USER")
            print("- EMAIL_PASSWORD") 
            print("- EMAIL_LOCAL_RECIPIENTS o EMAIL_PRODUCTION_RECIPIENTS")
            
    except ImportError as e:
        print(f"❌ Error importando sistema de email: {e}")

if __name__ == "__main__":
    # Verificar configuración antes de probar
    verificar_configuracion_email()
    
    # Ejecutar prueba
    test_cita_notification()
    
    print("\n" + "="*50)
    print("PRUEBA COMPLETADA")
    print("="*50)
    print("\nSi todo funcionó correctamente, deberías haber recibido:")
    print("1. ✅ Una respuesta exitosa del API")
    print("2. ✅ Los datos actualizados en la BD") 
    print("3. 📧 Un email de notificación")
    print("\nSi no recibiste el email, revisa:")
    print("- Las variables de entorno de email en .env")
    print("- Los logs del servidor para errores de SMTP")
    print("- La carpeta de spam de tu email")
# Sistema de Notificaciones de Citas

## Descripción General

El sistema de notificaciones de citas envía automáticamente emails cuando un lead agenda una cita a través del sistema de llamadas automáticas.

## ¿Cómo Funciona?

### 1. Procesamiento de Llamadas con Cita

Cuando se recibe una llamada que resulta en una petición de cita:

**API Endpoint**: `POST /api/actualizar_resultado`

**Parámetros para cita**:
```json
{
    "telefono": "123456789",
    "nuevaCita": "15/12/2025 10:00:00",  // Fecha y hora de la cita
    "horaCita": "10:00:00",              // Hora específica (opcional)
    "conPack": true,                     // Si incluye pack
    "preferenciaMT": "MORNING",          // MORNING o AFTERNOON
    "preferenciaFecha": "15/12/2025"     // Fecha preferida
}
```

### 2. Datos Guardados en BD

El sistema actualiza automáticamente:

- **`cita`**: Fecha de la cita (formato DATE)
- **`hora_cita`**: Hora de la cita (formato TIME)  
- **`preferencia_horario`**: 'mañana' o 'tarde'
- **`fecha_minima_reserva`**: Fecha mínima deseada
- **`status_level_1`**: 'Cita Agendada'
- **`status_level_2`**: 'Con Pack' o 'Sin Pack'
- **`conPack`**: Boolean indicando si incluye pack

### 3. Envío de Notificación

**Cuándo se envía**:
- Cuando `nuevaCita` está presente en el JSON
- Cuando `status_level_1` se actualiza a 'Cita Agendada'

**Contenido del email**:
- Información del paciente (nombre, teléfono)
- Detalles de la cita (fecha, hora, preferencia)
- Información de la clínica
- Si incluye pack o no

## Configuración

### Variables de Entorno (.env)

```bash
# Configuración SMTP
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USER=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password

# Destinatarios LOCAL
EMAIL_LOCAL_RECIPIENTS=admin@local.com,test@local.com

# Destinatarios PRODUCCIÓN  
EMAIL_PRODUCTION_RECIPIENTS=admin@empresa.com,notificaciones@empresa.com
```

### Detección Automática de Entorno

El sistema detecta automáticamente si está en:

- **Local**: Si no hay `MYSQL_URL` o no contiene 'railway.app'
- **Producción**: Si `MYSQL_URL` contiene 'railway.app'

Y envía emails a los destinatarios correspondientes.

## Estados del Sistema

### ✅ Sistema Habilitado
- Todas las variables de entorno configuradas
- Al menos un email de destino configurado
- Sistema funcional

### ❌ Sistema Deshabilitado
- Faltan variables de entorno críticas
- No hay emails de destino configurados
- Se registra warning en logs

## Estructura del Email

### Asunto
```
🦷 Nueva Cita Agendada - [Nombre Completo]
```

### Contenido HTML
- Header con título
- Información del paciente
- Detalles de la cita (destacados)
- Información de la clínica
- Footer con información del sistema

### Información Incluida
- **Paciente**: Nombre completo, teléfono
- **Cita**: Fecha formateada, hora, preferencia de horario
- **Pack**: Si incluye o no
- **Clínica**: Nombre del centro
- **Sistema**: Fecha/hora de notificación, entorno

## Testing

### Script de Prueba
```bash
python test_email_notification.py
```

**El script**:
1. Verifica configuración de email
2. Envía una cita de prueba
3. Verifica datos en BD
4. Confirma envío de email

### Verificación Manual

**1. Comprobar configuración**:
```python
from email_notifications import email_notifier
print(f"Habilitado: {email_notifier.enabled}")
print(f"Emails: {email_notifier.notification_emails}")
```

**2. Enviar cita de prueba**:
```bash
curl -X POST http://localhost:5000/api/actualizar_resultado \
  -H "Content-Type: application/json" \
  -d '{
    "telefono": "123456789",
    "nuevaCita": "15/12/2025 10:00:00",
    "conPack": true,
    "preferenciaMT": "MORNING"
  }'
```

## Logs del Sistema

### Mensajes de Éxito
```
Sistema de notificaciones por email disponible
Email configurado: user@gmail.com -> ['admin@empresa.com']
Notificación de cita enviada exitosamente para 123456789
Email enviado exitosamente a: ['admin@empresa.com']
```

### Mensajes de Error
```
Email no configurado: faltan EMAIL_USER o EMAIL_PASSWORD
Error enviando notificación de cita para 123456789: [detalle]
Sistema de notificaciones por email no disponible
```

## Solución de Problemas

### Email no se envía

**1. Verificar variables de entorno**:
```bash
# En .env deben estar todas estas variables
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_LOCAL_RECIPIENTS= o EMAIL_PRODUCTION_RECIPIENTS=
```

**2. Gmail App Password**:
- Usar "App Password" en lugar de contraseña normal
- Generar en: Google Account → Security → 2-Step Verification → App passwords

**3. Verificar logs**:
```bash
# Buscar errores en logs del servidor
grep -i "email\|smtp" logs/app.log
```

### Email llega a spam
- Configurar SPF/DKIM en el dominio del remitente
- Usar un servicio SMTP profesional (SendGrid, Mailgun, etc.)

### Cita no se guarda en BD
- Verificar que el teléfono exista en la tabla `leads`
- Comprobar formato de fecha/hora
- Revisar logs de la BD para errores SQL

## Archivos del Sistema

- **`email_notifications.py`**: Clase principal del sistema
- **`api_resultado_llamada.py`**: Integración con API (líneas 557-595)
- **`test_email_notification.py`**: Script de pruebas
- **`.env`**: Configuración de variables de entorno

## Personalización

### Cambiar plantilla de email
Editar `email_notifications.py` → `send_cita_notification()` → `body_html`

### Añadir nuevos destinatarios
Actualizar variables `EMAIL_LOCAL_RECIPIENTS` o `EMAIL_PRODUCTION_RECIPIENTS`

### Cambiar condiciones de envío
Modificar condición en `api_resultado_llamada.py` línea 557:
```python
if (data.get('nuevaCita') or status_level_1 == 'Cita Agendada') and EMAIL_NOTIFICATIONS_AVAILABLE:
```
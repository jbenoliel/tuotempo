import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Carga variables de entorno desde .env en desarrollo local
load_dotenv()

class Settings:
    """Configuración de la aplicación y base de datos"""
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia_este_valor_en_produccion")

    # Base de datos MySQL - Lógica robusta para Railway y local
    MYSQL_URL = os.environ.get("MYSQL_URL")

    if MYSQL_URL:
        # Si estamos en Railway (o un entorno con URL de conexión)
        url = urlparse(MYSQL_URL)
        DB_HOST = url.hostname
        DB_PORT = url.port or 3306
        DB_USER = url.username
        DB_PASSWORD = url.password
        DB_DATABASE = url.path[1:] if url.path else None # Eliminar la barra inicial y manejar path vacío
    else:
        # Si estamos en local, usar las variables individuales
        DB_HOST = os.environ.get("MYSQL_HOST", os.environ.get("MYSQLHOST", "localhost"))
        DB_PORT = int(os.environ.get("MYSQL_PORT", os.environ.get("MYSQLPORT", 3306)))
        DB_USER = os.environ.get("MYSQL_USER", os.environ.get("MYSQLUSER", "root"))
        DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", os.environ.get("MYSQLPASSWORD", ""))
        DB_DATABASE = os.environ.get("MYSQL_DATABASE", os.environ.get("MYSQLDATABASE", "Segurcaixa"))

settings = Settings()

# Documentación de la estructura de base de datos
DB_SCHEMA_DESCRIPTION = """
# Estructura de Base de Datos - TuoTempo

## Tabla: leads
**Tabla principal de leads/clientes potenciales**

### Campos básicos:
- `id`: INT AUTO_INCREMENT PRIMARY KEY - Identificador único
- `nombre`: VARCHAR(100) - Nombre del cliente
- `apellidos`: VARCHAR(150) - Apellidos del cliente
- `telefono`: VARCHAR(20) - Teléfono principal
- `telefono2`: VARCHAR(20) - Teléfono secundario
- `email`: VARCHAR(100) - Correo electrónico
- `nif`: VARCHAR(20) - Número de identificación
- `fecha_nacimiento`: DATE - Fecha de nacimiento
- `sexo`: VARCHAR(10) - Género

### Campos de ubicación y clínica:
- `ciudad`: VARCHAR(100) - Ciudad del cliente
- `codigo_postal`: VARCHAR(10) - Código postal
- `nombre_clinica`: VARCHAR(200) - Nombre de la clínica asignada
- `direccion_clinica`: TEXT - Dirección de la clínica
- `clinica_id`: INT - ID de la clínica
- `area_id`: INT - ID del área geográfica
- `delegacion`: VARCHAR(100) - Delegación asignada

### Campos de seguro y póliza:
- `certificado`: VARCHAR(50) - Número de certificado
- `poliza`: VARCHAR(50) - Número de póliza
- `segmento`: VARCHAR(50) - Segmento del cliente
- `conPack`: TINYINT(1) DEFAULT 0 - Si tiene pack contratado

### Campos de cita:
- `cita`: DATE - Fecha de la cita
- `hora_cita`: TIME - Hora de la cita

### Campos de estado y resultado:
- `status_level_1`: VARCHAR(100) - Estado principal (Volver a llamar, No Interesado, Cita Agendada, etc.)
- `status_level_2`: VARCHAR(100) - Subestado detallado
- `ultimo_estado`: VARCHAR(100) - Último estado registrado
- `resultado_llamada`: VARCHAR(100) - Resultado de la última llamada
- `hora_rellamada`: DATETIME - Fecha y hora programada para rellamar
- `error_tecnico`: TEXT - Descripción de errores técnicos
- `razon_vuelta_a_llamar`: TEXT - Razón por la que hay que volver a llamar
- `razon_no_interes`: TEXT - Razón de falta de interés

### Campos del sistema de llamadas (Pearl AI):
- `call_status`: ENUM('no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer') DEFAULT 'no_selected' - Estado de la llamada automática
- `call_priority`: INT DEFAULT 3 - Prioridad de llamada (1=Alta, 3=Normal, 5=Baja)
- `selected_for_calling`: BOOLEAN DEFAULT FALSE - Si está seleccionado para llamar
- `pearl_outbound_id`: VARCHAR(100) - ID de la campaña outbound de Pearl AI
- `last_call_attempt`: DATETIME - Fecha del último intento de llamada
- `call_attempts_count`: INT DEFAULT 0 - Número de intentos realizados
- `call_error_message`: TEXT - Último mensaje de error
- `pearl_call_response`: TEXT - Respuesta completa de Pearl AI
- `call_notes`: TEXT - Notas adicionales sobre la llamada
- `manual_management`: BOOLEAN DEFAULT FALSE - Si se gestiona manualmente (excluido de llamadas automáticas)

### Campos del sistema de scheduler:
- `lead_status`: ENUM('open', 'closed') DEFAULT 'open' - Estado del lead (abierto/cerrado)
- `closure_reason`: VARCHAR(100) - Razón de cierre ('Teléfono erróneo', 'Ilocalizable', 'No colabora')

### Campos de sistema:
- `match_source`: VARCHAR(100) - Fuente del lead
- `match_confidence`: DECIMAL(3,2) - Nivel de confianza del matching
- `call_id`: VARCHAR(50) - ID de la llamada
- `call_time`: DATETIME - Tiempo de la llamada
- `call_duration`: INT - Duración en segundos
- `call_summary`: TEXT - Resumen de la llamada
- `call_recording_url`: VARCHAR(500) - URL de grabación
- `orden`: INT - Orden de procesamiento
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP - Última actualización

### Índices:
- `idx_call_status`: Índice en call_status
- `idx_selected_for_calling`: Índice en selected_for_calling  
- `idx_call_priority`: Índice en call_priority
- `idx_last_call_attempt`: Índice en last_call_attempt
- `idx_pearl_outbound_id`: Índice en pearl_outbound_id
- `idx_lead_status`: Índice en lead_status
- `idx_closure_reason`: Índice en closure_reason

## Tabla: call_schedule
**Programación automática de llamadas**

- `id`: INT AUTO_INCREMENT PRIMARY KEY
- `lead_id`: INT NOT NULL - FK a leads(id)
- `scheduled_at`: DATETIME NOT NULL - Fecha/hora programada
- `attempt_number`: INT NOT NULL - Número de intento
- `status`: ENUM('pending', 'completed', 'failed', 'cancelled') DEFAULT 'pending'
- `last_outcome`: VARCHAR(50) - Resultado del último intento
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

### Índices:
- `idx_scheduled_at`: Índice en scheduled_at
- `idx_lead_status`: Índice en (lead_id, status)
- `idx_status_scheduled`: Índice en (status, scheduled_at)

## Tabla: scheduler_config
**Configuración del scheduler**

- `id`: INT AUTO_INCREMENT PRIMARY KEY
- `config_key`: VARCHAR(50) UNIQUE NOT NULL - Clave de configuración
- `config_value`: TEXT NOT NULL - Valor de configuración
- `description`: TEXT - Descripción de la configuración
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

### Configuraciones por defecto:
- `working_hours_start`: '10:00' - Hora inicio llamadas
- `working_hours_end`: '20:00' - Hora fin llamadas  
- `reschedule_hours`: '30' - Horas entre intentos
- `max_attempts`: '6' - Máximo intentos antes de cerrar
- `closure_reasons`: JSON con razones de cierre
- `working_days`: JSON con días laborables [1,2,3,4,5]

## Tabla: pearl_calls
**Registro de llamadas de Pearl AI**

- `id`: INT AUTO_INCREMENT PRIMARY KEY
- `call_id`: VARCHAR(64) UNIQUE NOT NULL - ID único de Pearl AI
- `phone_number`: VARCHAR(20) NOT NULL - Número llamado
- `lead_id`: INT - FK a leads(id) (puede ser NULL)
- `outbound_id`: VARCHAR(100) - ID de campaña outbound
- `status`: VARCHAR(50) - Estado de la llamada
- `duration`: INT - Duración en segundos
- `cost`: DECIMAL(10,4) - Costo de la llamada
- `recording_url`: VARCHAR(500) - URL de grabación
- `summary`: TEXT - Resumen de la llamada
- `transcription`: TEXT - Transcripción completa
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

## Tabla: usuarios
**Usuarios del sistema**

- `id`: INT AUTO_INCREMENT PRIMARY KEY
- `username`: VARCHAR(50) NOT NULL UNIQUE - Nombre de usuario
- `password_hash`: VARCHAR(255) NOT NULL - Hash de la contraseña
- `email`: VARCHAR(100) - Correo electrónico
- `full_name`: VARCHAR(200) - Nombre completo
- `is_active`: BOOLEAN DEFAULT TRUE - Usuario activo
- `role`: VARCHAR(50) DEFAULT 'user' - Rol del usuario
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

## Tabla: daemon_status
**Estado de daemons del sistema**

- `id`: INT AUTO_INCREMENT PRIMARY KEY
- `daemon_name`: VARCHAR(100) NOT NULL - Nombre del daemon
- `is_running`: BOOLEAN DEFAULT FALSE - Si está ejecutándose
- `last_heartbeat`: DATETIME - Último heartbeat
- `process_id`: INT - ID del proceso
- `config_data`: JSON - Configuración del daemon
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
"""
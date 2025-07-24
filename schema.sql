-- Script para recrear la estructura completa de la base de datos.
-- Se puede ejecutar de forma segura, ya que elimina las tablas si ya existen.

-- Eliminar tablas en orden inverso para evitar problemas de claves foráneas
DROP TABLE IF EXISTS `pearl_calls`;
DROP TABLE IF EXISTS `recargas`;
DROP TABLE IF EXISTS `leads`;
DROP TABLE IF EXISTS `clinicas`;
DROP TABLE IF EXISTS `usuarios`;

-- --- Tabla de Usuarios ---
-- Almacena las credenciales para acceder al dashboard.
CREATE TABLE `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(80) UNIQUE NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) UNIQUE NULL,
  `is_admin` TINYINT(1) NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `email_verified` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --- Tabla de Clínicas ---
-- Almacena la información de todas las clínicas disponibles.
CREATE TABLE `clinicas` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `areaid` VARCHAR(255) NOT NULL COMMENT 'ID único del área/clínica',
  `areaTitle` VARCHAR(255) NOT NULL COMMENT 'Nombre de la clínica',
  `address` VARCHAR(255) NULL COMMENT 'Dirección de la clínica',
  `cp` VARCHAR(10) NOT NULL COMMENT 'Código postal',
  `city` VARCHAR(100) NOT NULL COMMENT 'Ciudad',
  `province` VARCHAR(100) NOT NULL COMMENT 'Provincia',
  `phone` VARCHAR(20) NULL COMMENT 'Teléfono de contacto',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_cp` (`cp`),
  INDEX `idx_city` (`city`),
  INDEX `idx_province` (`province`),
  UNIQUE KEY `unique_areaid` (`areaid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --- Tabla de Leads ---
-- Tabla principal que contiene todos los datos de los leads a contactar.
CREATE TABLE `leads` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(100) NULL,
  `apellidos` VARCHAR(150) NULL,
  `telefono` VARCHAR(20) NULL,
  `telefono2` VARCHAR(20) NULL,
  `nif` VARCHAR(20) NULL,
  `fecha_nacimiento` DATE NULL,
  `sexo` VARCHAR(10) NULL,
  `email` VARCHAR(255) NULL,
  `poliza` VARCHAR(50) NULL,
  `segmento` VARCHAR(100) NULL,
  `certificado` VARCHAR(100) NULL,
  `delegacion` VARCHAR(100) NULL,
  `clinica_id` VARCHAR(50) NULL,
  `nombre_clinica` VARCHAR(255) NULL,
  `direccion_clinica` VARCHAR(255) NULL,
  `codigo_postal` VARCHAR(10) NULL,
  `ciudad` VARCHAR(100) NULL,
  `area_id` VARCHAR(100) NULL,
  `match_source` VARCHAR(50) NULL,
  `match_confidence` INT NULL,
  `orden` INT NULL,
  `ultimo_estado` ENUM('no answer', 'busy', 'completed') NULL,
  `resultado_llamada` ENUM('volver a marcar', 'no interesado', 'cita sin pack', 'cita con pack') NULL,
  `status_level_1` VARCHAR(100) NULL,
  `status_level_2` VARCHAR(255) NULL,
  `cita` DATE NULL,
  `hora_cita` TIME NULL,
  `conPack` TINYINT(1) DEFAULT 0,
  `hora_rellamada` VARCHAR(50) NULL,
  `razon_vuelta_a_llamar` VARCHAR(255) NULL,
  `razon_no_interes` VARCHAR(255) NULL,
  `error_tecnico` VARCHAR(255) NULL,
  `call_id` VARCHAR(255) NULL,
  `call_time` DATETIME NULL,
  `call_duration` INT NULL,
  `call_summary` TEXT NULL,
  `call_recording_url` TEXT NULL,
  -- Campos para el sistema de llamadas automáticas con Pearl AI
  `call_status` ENUM('no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer') DEFAULT 'no_selected' COMMENT 'Estado actual de la llamada automática',
  `call_priority` INT DEFAULT 3 COMMENT 'Prioridad de llamada (1=Alta, 3=Normal, 5=Baja)',
  `selected_for_calling` BOOLEAN DEFAULT FALSE COMMENT 'Flag para indicar si el lead está seleccionado para llamar',
  `pearl_outbound_id` VARCHAR(100) NULL COMMENT 'ID de la campaña outbound de Pearl AI',
  `last_call_attempt` DATETIME NULL COMMENT 'Fecha y hora del último intento de llamada',
  `call_attempts_count` INT DEFAULT 0 COMMENT 'Número de intentos de llamada realizados',
  `call_error_message` TEXT NULL COMMENT 'Último mensaje de error en caso de fallo en la llamada',
  `pearl_call_response` TEXT NULL COMMENT 'Respuesta completa de la API de Pearl AI',
  `call_notes` TEXT NULL COMMENT 'Notas adicionales sobre la llamada',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Timestamp de última actualización del registro'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índices para optimizar consultas del sistema de llamadas
CREATE INDEX idx_call_status ON leads(call_status);
CREATE INDEX idx_selected_for_calling ON leads(selected_for_calling);
CREATE INDEX idx_call_priority ON leads(call_priority);
CREATE INDEX idx_last_call_attempt ON leads(last_call_attempt);
CREATE INDEX idx_pearl_outbound_id ON leads(pearl_outbound_id);

-- --- Tabla de Llamadas de Pearl --- 
-- Almacena un registro detallado de cada llamada gestionada a través de Pearl AI.
CREATE TABLE `pearl_calls` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `call_id` VARCHAR(64) NOT NULL UNIQUE COMMENT 'ID único de la llamada en Pearl AI',
  `phone_number` VARCHAR(20) NOT NULL COMMENT 'Número de teléfono al que se llamó',
  `call_time` DATETIME NOT NULL COMMENT 'Fecha y hora de la llamada',
  `duration` INT DEFAULT 0 COMMENT 'Duración de la llamada en segundos',
  `summary` TEXT COMMENT 'Resumen de la conversación generado por IA',
  `collected_info` JSON COMMENT 'Datos estructurados recogidos durante la llamada',
  `recording_url` VARCHAR(512) COMMENT 'URL de la grabación de la llamada',
  `lead_id` INT NULL COMMENT 'ID del lead asociado en nuestra BBDD',
  INDEX `idx_phone` (`phone_number`),
  CONSTRAINT `fk_pearl_calls_lead` FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --- Tabla de Recargas ---
-- Almacena un historial de todas las subidas de archivos Excel/CSV.
CREATE TABLE `recargas` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL,
  `fecha` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `archivo` VARCHAR(255) NOT NULL,
  `registros_importados` INT DEFAULT 0,
  `resultado` VARCHAR(50) NOT NULL,
  `mensaje` TEXT NULL,
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --- Datos Iniciales ---
-- Insertar un usuario administrador por defecto para poder iniciar sesión la primera vez.
-- La contraseña es 'admin'. ¡Cámbiala en un entorno de producción real!
-- La contraseña hash fue generada con: bcrypt.generate_password_hash('admin').decode('utf-8')
INSERT INTO `usuarios` (username, password_hash, is_admin, email_verified) VALUES ('admin', '$2b$12$DbmIZImk9bCbjH.L3hJzPO0wGkLz2O8H3a./2Y/i2r3sM0m2q9.iK', 1, 1);


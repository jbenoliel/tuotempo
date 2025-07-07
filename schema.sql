-- Script para recrear la estructura completa de la base de datos.
-- Se puede ejecutar de forma segura, ya que elimina las tablas si ya existen.

-- Eliminar tablas en orden inverso para evitar problemas de claves foráneas
DROP TABLE IF EXISTS `recargas`;
DROP TABLE IF EXISTS `leads`;
DROP TABLE IF EXISTS `usuarios`;

-- --- Tabla de Usuarios ---
-- Almacena las credenciales para acceder al dashboard.
CREATE TABLE `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(80) UNIQUE NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
  `cita` DATETIME NULL,
  `conPack` TINYINT(1) DEFAULT 0,
  `hora_rellamada` VARCHAR(50) NULL,
  `razon_vuelta_a_llamar` VARCHAR(255) NULL,
  `razon_no_interes` VARCHAR(255) NULL,
  `error_tecnico` VARCHAR(255) NULL,
  `call_id` VARCHAR(255) NULL,
  `call_time` DATETIME NULL,
  `call_duration` INT NULL,
  `call_summary` TEXT NULL,
  `call_recording_url` TEXT NULL
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
INSERT INTO `usuarios` (username, password_hash) VALUES ('admin', '$2b$12$DbmIZImk9bCbjH.L3hJzPO0wGkLz2O8H3a./2Y/i2r3sM0m2q9.iK');


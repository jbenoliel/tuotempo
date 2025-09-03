#!/usr/bin/env python3
"""
Migración simple para añadir campo origen_archivo sin emojis
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import pymysql

def get_connection():
    """Establecer conexión con la base de datos."""
    load_dotenv()
    
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQLHOST'),
            user=os.getenv('MYSQLUSER'),
            password=os.getenv('MYSQLPASSWORD'),
            database=os.getenv('MYSQLDATABASE'),
            port=int(os.getenv('MYSQLPORT')),
            charset='utf8mb4',
            autocommit=False
        )
        print(f"[OK] Conectado a BD: {os.getenv('MYSQLDATABASE')} en {os.getenv('MYSQLHOST')}")
        return conn
    except Exception as e:
        print(f"[ERROR] Error conectando a BD: {e}")
        return None

def run_migration():
    """Ejecutar la migración simple."""
    print("=== INICIANDO MIGRACION ORIGEN_ARCHIVO ===")
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 1. Verificar si ya existe el campo origen_archivo
        cursor.execute("SHOW COLUMNS FROM leads LIKE 'origen_archivo'")
        if cursor.fetchone():
            print("[INFO] Campo 'origen_archivo' ya existe, saltando...")
        else:
            # Añadir campo al final de la tabla
            print("[INFO] Añadiendo campo 'origen_archivo' a tabla leads...")
            cursor.execute("""
                ALTER TABLE `leads` 
                ADD COLUMN `origen_archivo` VARCHAR(255) NULL 
                COMMENT 'Nombre del archivo de origen de los datos'
            """)
            print("[OK] Campo 'origen_archivo' añadido")
        
        # 2. Crear tabla archivos_origen si no existe
        cursor.execute("SHOW TABLES LIKE 'archivos_origen'")
        if cursor.fetchone():
            print("[INFO] Tabla 'archivos_origen' ya existe, saltando...")
        else:
            print("[INFO] Creando tabla 'archivos_origen'...")
            cursor.execute("""
                CREATE TABLE `archivos_origen` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `nombre_archivo` VARCHAR(255) NOT NULL UNIQUE,
                    `descripcion` TEXT NULL,
                    `fecha_creacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `total_registros` INT DEFAULT 0,
                    `usuario_creacion` VARCHAR(100) NULL,
                    `activo` TINYINT(1) DEFAULT 1,
                    INDEX `idx_nombre_archivo` (`nombre_archivo`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("[OK] Tabla 'archivos_origen' creada")
        
        # 3. Crear índice si no existe
        try:
            cursor.execute("CREATE INDEX `idx_origen_archivo` ON `leads`(`origen_archivo`)")
            print("[OK] Índice creado para origen_archivo")
        except:
            print("[INFO] Índice ya existe para origen_archivo")
        
        # 4. Actualizar datos existentes si no tienen origen
        cursor.execute("SELECT COUNT(*) FROM leads WHERE origen_archivo IS NULL")
        count_null = cursor.fetchone()[0]
        
        if count_null > 0:
            print(f"[INFO] Actualizando {count_null} registros sin origen_archivo...")
            cursor.execute("""
                UPDATE `leads` 
                SET `origen_archivo` = 'SEGURCAIXA_JULIO' 
                WHERE `origen_archivo` IS NULL
            """)
            
            # Registrar archivo origen
            cursor.execute("""
                INSERT IGNORE INTO `archivos_origen` 
                (nombre_archivo, descripcion, total_registros, usuario_creacion)
                VALUES ('SEGURCAIXA_JULIO', 'Datos históricos de Segurcaixa', %s, 'sistema')
            """, (count_null,))
            
            print(f"[OK] {count_null} registros actualizados con SEGURCAIXA_JULIO")
        else:
            print("[INFO] Todos los registros ya tienen origen_archivo")
        
        # Confirmar cambios
        conn.commit()
        print("[OK] Migración completada exitosamente")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante migración: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
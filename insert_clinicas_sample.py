#!/usr/bin/env python3
"""
Script para insertar datos de ejemplo en la tabla de clínicas.
Basado en el formato proporcionado por el usuario.
"""

import mysql.connector
from config import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Datos de ejemplo basados en el formato proporcionado
clinicas_sample = [
    {
        "areaid": "default@tt_adeslas_e5eui6cu_evyefjct_e2iclhex_pm2exhng_lerl",
        "areaTitle": "Adeslas Dental Andujar",
        "address": "Calle Ollerías, 45",
        "cp": "23740",
        "city": "Andujar",
        "province": "Jaen",
        "phone": "953500123"
    },
    {
        "areaid": "default@tt_adeslas_madrid_centro_001",
        "areaTitle": "Adeslas Dental Madrid Centro",
        "address": "Calle Gran Vía, 123",
        "cp": "28013",
        "city": "Madrid",
        "province": "Madrid",
        "phone": "915551234"
    },
    {
        "areaid": "default@tt_adeslas_barcelona_eixample_001",
        "areaTitle": "Adeslas Dental Barcelona Eixample",
        "address": "Carrer de Balmes, 456",
        "cp": "08007",
        "city": "Barcelona",
        "province": "Barcelona",
        "phone": "934567890"
    },
    {
        "areaid": "default@tt_adeslas_sevilla_centro_001",
        "areaTitle": "Adeslas Dental Sevilla Centro",
        "address": "Calle Sierpes, 78",
        "cp": "41004",
        "city": "Sevilla",
        "province": "Sevilla",
        "phone": "954123456"
    },
    {
        "areaid": "default@tt_adeslas_valencia_centro_001",
        "areaTitle": "Adeslas Dental Valencia Centro",
        "address": "Calle Colón, 234",
        "cp": "46004",
        "city": "Valencia",
        "province": "Valencia",
        "phone": "963789012"
    }
]

def insert_clinicas():
    """Inserta las clínicas de ejemplo en la base de datos"""
    conn = get_db_connection()
    if not conn:
        logger.error("No se pudo conectar a la base de datos")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Consulta de inserción
        insert_query = """
            INSERT INTO clinicas (areaid, areaTitle, address, cp, city, province, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                areaTitle = VALUES(areaTitle),
                address = VALUES(address),
                cp = VALUES(cp),
                city = VALUES(city),
                province = VALUES(province),
                phone = VALUES(phone),
                updated_at = CURRENT_TIMESTAMP
        """
        
        # Insertar cada clínica
        insertadas = 0
        actualizadas = 0
        
        for clinica in clinicas_sample:
            try:
                cursor.execute(insert_query, (
                    clinica['areaid'],
                    clinica['areaTitle'],
                    clinica['address'],
                    clinica['cp'],
                    clinica['city'],
                    clinica['province'],
                    clinica.get('phone', '')
                ))
                
                if cursor.rowcount == 1:
                    insertadas += 1
                    logger.info(f"✅ Insertada: {clinica['areaTitle']} - {clinica['city']}")
                elif cursor.rowcount == 2:
                    actualizadas += 1
                    logger.info(f"🔄 Actualizada: {clinica['areaTitle']} - {clinica['city']}")
                    
            except mysql.connector.Error as err:
                logger.error(f"❌ Error insertando {clinica['areaTitle']}: {err}")
        
        conn.commit()
        logger.info(f"\n📊 Resumen:")
        logger.info(f"   Clínicas insertadas: {insertadas}")
        logger.info(f"   Clínicas actualizadas: {actualizadas}")
        logger.info(f"   Total procesadas: {len(clinicas_sample)}")
        
        return True
        
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        conn.rollback()
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def main():
    """Función principal"""
    logger.info("🏥 Insertando datos de clínicas de ejemplo...")
    
    if insert_clinicas():
        logger.info("✅ Proceso completado exitosamente")
    else:
        logger.error("❌ Error durante el proceso")

if __name__ == "__main__":
    main()

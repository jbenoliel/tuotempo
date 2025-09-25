"""
Script para verificar si un teléfono existe en la base de datos y cómo está almacenado.
Útil para debuggear problemas de búsqueda de leads.
"""

import mysql.connector
import os
import re
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Establece conexión con la base de datos MySQL"""
    try:
        DB_CONFIG = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'tuotempo'),
            'ssl_disabled': True,
            'autocommit': True,
            'charset': 'utf8mb4',
            'use_unicode': True
        }

        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def normalizar_telefono(telefono):
    """Normaliza un teléfono eliminando caracteres no numéricos"""
    if not telefono:
        return ""
    telefono_digits = re.sub(r'\D', '', str(telefono))
    # Conservar los 9 dígitos finales si hay más
    if len(telefono_digits) > 9:
        telefono_digits = telefono_digits[-9:]
    return telefono_digits

def buscar_telefono_en_bd(telefono_original):
    """
    Busca un teléfono en la base de datos usando diferentes estrategias.

    Args:
        telefono_original (str): Teléfono original (ej: +34629203315)
    """

    print(f"=== VERIFICACIÓN DE TELÉFONO ===")
    print(f"Teléfono original: {telefono_original}")

    # Normalizar teléfono (igual que hace la API)
    telefono_normalizado = normalizar_telefono(telefono_original)
    print(f"Teléfono normalizado: {telefono_normalizado}")

    conn = get_db_connection()
    if not conn:
        print("[ERROR] No se pudo conectar a la base de datos")
        return

    try:
        cursor = conn.cursor(dictionary=True)

        # Estrategia 1: Búsqueda exacta por teléfono
        print(f"\n1. Busqueda exacta por telefono = '{telefono_normalizado}'")
        cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads WHERE telefono = %s LIMIT 5", (telefono_normalizado,))
        results = cursor.fetchall()

        if results:
            print(f"✅ Encontrados {len(results)} leads:")
            for lead in results:
                print(f"   ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: '{lead['telefono']}' | Tel2: '{lead['telefono2']}'")
        else:
            print("❌ No se encontraron leads con búsqueda exacta")

        # Estrategia 2: Búsqueda exacta por telefono2
        print(f"\n2️⃣ Búsqueda exacta por telefono2 = '{telefono_normalizado}'")
        cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads WHERE telefono2 = %s LIMIT 5", (telefono_normalizado,))
        results2 = cursor.fetchall()

        if results2:
            print(f"✅ Encontrados {len(results2)} leads en telefono2:")
            for lead in results2:
                print(f"   ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: '{lead['telefono']}' | Tel2: '{lead['telefono2']}'")
        else:
            print("❌ No se encontraron leads en telefono2")

        # Estrategia 3: Búsqueda con REGEXP (igual que usa la API)
        print(f"\n3️⃣ Búsqueda con REGEXP (como usa la API)")
        cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads WHERE REGEXP_REPLACE(telefono, '[^0-9]', '') = %s LIMIT 5", (telefono_normalizado,))
        results3 = cursor.fetchall()

        if results3:
            print(f"✅ Encontrados {len(results3)} leads con REGEXP en telefono:")
            for lead in results3:
                print(f"   ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: '{lead['telefono']}' | Tel2: '{lead['telefono2']}'")
        else:
            print("❌ No se encontraron leads con REGEXP en telefono")

        # Estrategia 4: Búsqueda con REGEXP en telefono2
        print(f"\n4️⃣ Búsqueda con REGEXP en telefono2")
        cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads WHERE REGEXP_REPLACE(telefono2, '[^0-9]', '') = %s LIMIT 5", (telefono_normalizado,))
        results4 = cursor.fetchall()

        if results4:
            print(f"✅ Encontrados {len(results4)} leads con REGEXP en telefono2:")
            for lead in results4:
                print(f"   ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: '{lead['telefono']}' | Tel2: '{lead['telefono2']}'")
        else:
            print("❌ No se encontraron leads con REGEXP en telefono2")

        # Estrategia 5: Búsqueda parcial (contiene los dígitos)
        print(f"\n5️⃣ Búsqueda parcial (que contenga '{telefono_normalizado}')")
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, telefono2
            FROM leads
            WHERE telefono LIKE %s OR telefono2 LIKE %s
            LIMIT 10
        """, (f'%{telefono_normalizado}%', f'%{telefono_normalizado}%'))
        results5 = cursor.fetchall()

        if results5:
            print(f"✅ Encontrados {len(results5)} leads con búsqueda parcial:")
            for lead in results5:
                print(f"   ID: {lead['id']} | Nombre: {lead['nombre']} {lead['apellidos']} | Tel1: '{lead['telefono']}' | Tel2: '{lead['telefono2']}'")
        else:
            print("❌ No se encontraron leads con búsqueda parcial")

        # Estrategia 6: Buscar teléfonos similares (para debug)
        print(f"\n6️⃣ Teléfonos similares en la BD (primeros 10)")
        cursor.execute("""
            SELECT telefono, telefono2, COUNT(*) as count
            FROM leads
            WHERE telefono IS NOT NULL AND telefono != ''
            GROUP BY telefono, telefono2
            ORDER BY count DESC
            LIMIT 10
        """)
        phone_samples = cursor.fetchall()

        if phone_samples:
            print("📞 Muestra de teléfonos en la BD:")
            for sample in phone_samples:
                print(f"   Tel1: '{sample['telefono']}' | Tel2: '{sample['telefono2']}' | Count: {sample['count']}")

        # Estadísticas generales
        print(f"\n📊 ESTADÍSTICAS GENERALES:")
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()['total']
        print(f"Total leads en BD: {total}")

        cursor.execute("SELECT COUNT(*) as count FROM leads WHERE telefono IS NOT NULL AND telefono != ''")
        with_phone = cursor.fetchone()['count']
        print(f"Leads con teléfono: {with_phone}")

        cursor.execute("SELECT COUNT(*) as count FROM leads WHERE telefono2 IS NOT NULL AND telefono2 != ''")
        with_phone2 = cursor.fetchone()['count']
        print(f"Leads con teléfono2: {with_phone2}")

    except mysql.connector.Error as e:
        print(f"Error en consulta: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def main():
    """Función principal"""
    import sys

    # Teléfono por defecto del problema reportado
    telefono = "+34629203315"

    # Permitir teléfono personalizado como argumento
    if len(sys.argv) > 1:
        telefono = sys.argv[1]

    print("VERIFICADOR DE TELEFONOS EN BD")
    print("Este script busca un telefono en la base de datos usando diferentes estrategias")
    print()

    buscar_telefono_en_bd(telefono)

if __name__ == "__main__":
    main()
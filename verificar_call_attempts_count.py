"""
Script para verificar que el campo call_attempts_count en la tabla leads
está correcto comparándolo con el número real de llamadas en pearl_calls.
"""

import os
import sys
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Crear conexión a la base de datos Railway"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQLHOST'),
            port=int(os.getenv('MYSQLPORT')),
            user=os.getenv('MYSQLUSER'),
            password=os.getenv('MYSQLPASSWORD'),
            database=os.getenv('MYSQLDATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

def verificar_call_attempts_count():
    """
    Verifica que el campo call_attempts_count esté correcto
    comparando con el número real de llamadas en pearl_calls
    """

    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            print("=== VERIFICACION DE CALL_ATTEMPTS_COUNT ===")
            print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # Consulta para comparar call_attempts_count con llamadas reales
            query = """
            SELECT
                l.id as lead_id,
                l.nombre,
                l.apellidos,
                l.telefono,
                l.call_attempts_count as contador_registrado,
                l.lead_status,
                l.status_level_1,
                l.last_call_attempt,
                pc_count.llamadas_reales,
                l.call_attempts_count - COALESCE(pc_count.llamadas_reales, 0) as diferencia
            FROM leads l
            LEFT JOIN (
                SELECT
                    CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci as phone_clean,
                    COUNT(*) as llamadas_reales
                FROM pearl_calls
                GROUP BY CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci
            ) pc_count ON CONVERT(REGEXP_REPLACE(l.telefono, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci = pc_count.phone_clean
            WHERE l.call_attempts_count > 0 OR pc_count.llamadas_reales > 0
            HAVING l.call_attempts_count != COALESCE(pc_count.llamadas_reales, 0)
            ORDER BY ABS(l.call_attempts_count - COALESCE(pc_count.llamadas_reales, 0)) DESC
            LIMIT 50
            """

            cursor.execute(query)
            discrepancias = cursor.fetchall()

            print(f"LEADS CON DISCREPANCIAS: {len(discrepancias)}")
            print("-" * 100)

            discrepancias_positivas = 0
            discrepancias_negativas = 0

            for lead in discrepancias:
                diferencia = lead['diferencia']

                if diferencia > 0:
                    discrepancias_positivas += 1
                    tipo = "SOBRE-CONTADO"
                else:
                    discrepancias_negativas += 1
                    tipo = "SUB-CONTADO"

                print(f"ID: {lead['lead_id']} | {lead['nombre']} {lead['apellidos']} | Tel: {lead['telefono']}")
                print(f"  Registrado: {lead['contador_registrado']} | Reales: {lead['llamadas_reales']} | Diferencia: {diferencia} ({tipo})")
                print(f"  Status: {lead['lead_status']} | Level 1: {lead['status_level_1']}")
                print(f"  Último intento: {lead['last_call_attempt']}")
                print()

            # Estadísticas generales
            print("\n=== ESTADISTICAS GENERALES ===")

            cursor.execute("""
                SELECT
                    COUNT(*) as total_leads,
                    SUM(CASE WHEN call_attempts_count > 0 THEN 1 ELSE 0 END) as leads_con_intentos,
                    AVG(call_attempts_count) as promedio_intentos,
                    MAX(call_attempts_count) as maximo_intentos
                FROM leads
            """)
            stats_leads = cursor.fetchone()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_llamadas,
                    COUNT(DISTINCT phone_number) as telefonos_unicos,
                    MIN(call_time) as primera_llamada,
                    MAX(call_time) as ultima_llamada
                FROM pearl_calls
            """)
            stats_calls = cursor.fetchone()

            print(f"Total leads: {stats_leads['total_leads']}")
            print(f"Leads con intentos registrados: {stats_leads['leads_con_intentos']}")
            print(f"Promedio intentos por lead: {stats_leads['promedio_intentos']:.2f}")
            print(f"Máximo intentos registrados: {stats_leads['maximo_intentos']}")
            print()
            print(f"Total llamadas en pearl_calls: {stats_calls['total_llamadas']}")
            print(f"Teléfonos únicos llamados: {stats_calls['telefonos_unicos']}")
            print(f"Primera llamada: {stats_calls['primera_llamada']}")
            print(f"Última llamada: {stats_calls['ultima_llamada']}")
            print()
            print(f"Discrepancias encontradas: {len(discrepancias)}")
            print(f"  - Sobre-contados (más intentos registrados que reales): {discrepancias_positivas}")
            print(f"  - Sub-contados (menos intentos registrados que reales): {discrepancias_negativas}")

            # Verificar leads sin intentos pero con llamadas reales
            print("\n=== LEADS SIN INTENTOS REGISTRADOS PERO CON LLAMADAS ===")
            cursor.execute("""
                SELECT
                    l.id,
                    l.nombre,
                    l.telefono,
                    l.call_attempts_count,
                    pc_count.llamadas_reales
                FROM leads l
                INNER JOIN (
                    SELECT
                        CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci as phone_clean,
                        COUNT(*) as llamadas_reales
                    FROM pearl_calls
                    GROUP BY CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci
                ) pc_count ON CONVERT(REGEXP_REPLACE(l.telefono, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci = pc_count.phone_clean
                WHERE (l.call_attempts_count = 0 OR l.call_attempts_count IS NULL) AND pc_count.llamadas_reales > 0
                LIMIT 10
            """)

            sin_registro = cursor.fetchall()
            print(f"Leads con llamadas pero sin intentos registrados: {len(sin_registro)}")
            for lead in sin_registro:
                print(f"  ID: {lead['id']} | {lead['nombre']} | Tel: {lead['telefono']} | Llamadas: {lead['llamadas_reales']}")

    except Exception as e:
        print(f"Error durante la verificación: {e}")
    finally:
        connection.close()

def corregir_discrepancias():
    """
    Corrige las discrepancias encontradas basándose en llamadas reales
    """
    print("\n=== CORRIGIENDO DISCREPANCIAS ===")
    print("Actualizando call_attempts_count basándose en llamadas reales de pearl_calls...")

    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            # Primero mostrar el antes y después para algunos casos
            print("\nEjemplos de correcciones que se aplicarán:")
            cursor.execute("""
            SELECT
                l.id,
                l.nombre,
                l.call_attempts_count as contador_actual,
                COALESCE(pc_count.llamadas_reales, 0) as contador_correcto
            FROM leads l
            LEFT JOIN (
                SELECT
                    CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci as phone_clean,
                    COUNT(*) as llamadas_reales
                FROM pearl_calls
                GROUP BY CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci
            ) pc_count ON CONVERT(REGEXP_REPLACE(l.telefono, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci = pc_count.phone_clean
            WHERE l.call_attempts_count != COALESCE(pc_count.llamadas_reales, 0)
            ORDER BY ABS(l.call_attempts_count - COALESCE(pc_count.llamadas_reales, 0)) DESC
            LIMIT 10
            """)

            ejemplos = cursor.fetchall()
            for ej in ejemplos:
                print(f"  ID {ej['id']} ({ej['nombre']}): {ej['contador_actual']} -> {ej['contador_correcto']}")

            # Actualizar todos los contadores basándose en pearl_calls
            print("\nEjecutando corrección masiva...")

            update_query = """
            UPDATE leads l
            LEFT JOIN (
                SELECT
                    CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci as phone_clean,
                    COUNT(*) as llamadas_reales
                FROM pearl_calls
                GROUP BY CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci
            ) pc_count ON CONVERT(REGEXP_REPLACE(l.telefono, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci = pc_count.phone_clean
            SET l.call_attempts_count = COALESCE(pc_count.llamadas_reales, 0)
            WHERE l.call_attempts_count != COALESCE(pc_count.llamadas_reales, 0)
            """

            cursor.execute(update_query)
            registros_actualizados = cursor.rowcount

            connection.commit()

            print(f"Actualizados {registros_actualizados} registros.")
            print("Correccion completada exitosamente.")

            # Verificar el resultado
            print("\nVerificando resultado...")
            cursor.execute("""
            SELECT COUNT(*) as discrepancias_restantes
            FROM leads l
            LEFT JOIN (
                SELECT
                    CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci as phone_clean,
                    COUNT(*) as llamadas_reales
                FROM pearl_calls
                GROUP BY CONVERT(REGEXP_REPLACE(phone_number, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci
            ) pc_count ON CONVERT(REGEXP_REPLACE(l.telefono, '[^0-9]', '') USING utf8mb4) COLLATE utf8mb4_unicode_ci = pc_count.phone_clean
            WHERE l.call_attempts_count != COALESCE(pc_count.llamadas_reales, 0)
            """)

            resultado = cursor.fetchone()
            print(f"Discrepancias restantes: {resultado['discrepancias_restantes']}")

    except Exception as e:
        print(f"Error durante la corrección: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    print("VERIFICADOR DE CALL_ATTEMPTS_COUNT")
    print("=" * 40)

    # Verificar discrepancias
    verificar_call_attempts_count()

    # Corregir discrepancias
    corregir_discrepancias()
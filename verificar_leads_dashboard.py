#!/usr/bin/env python3
"""
Script para verificar exactamente dónde aparecen los 31 leads "huérfanos" en las consultas del dashboard
"""

import pymysql
import logging
from datetime import datetime
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def verificar_leads_en_dashboard():
    """Verificar dónde aparecen exactamente los leads huérfanos en el dashboard"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== VERIFICACIÓN DE LEADS HUÉRFANOS EN CONSULTAS DEL DASHBOARD ===")

            # 1. Obtener los IDs de los 31 leads huérfanos
            cursor.execute("""
                SELECT id
                FROM leads
                WHERE
                    status_level_1 IS NULL
                    OR TRIM(status_level_1) = ''
                    OR TRIM(status_level_1) = 'None'
                ORDER BY id
            """)

            leads_huerfanos = [row['id'] for row in cursor.fetchall()]
            print(f"\n1. IDs DE LEADS HUÉRFANOS: {leads_huerfanos}")
            print(f"   Total: {len(leads_huerfanos)} leads")

            # 2. Obtener configuración de max_attempts
            cursor.execute("SELECT config_value FROM scheduler_config WHERE config_key = 'max_attempts'")
            row_max = cursor.fetchone()
            max_attempts = int(row_max['config_value']) if row_max else 6
            print(f"   Max attempts configurado: {max_attempts}")

            # 3. Verificar cada consulta específica del dashboard

            # 3.1 Consulta de CONTACTADOS (status_level_1 IS NOT NULL AND <> '' AND <> 'None')
            placeholders = ','.join(['%s'] * len(leads_huerfanos))
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND status_level_1 IS NOT NULL
                AND TRIM(status_level_1) <> ''
                AND TRIM(status_level_1) <> 'None'
            """, leads_huerfanos)
            contactados_count = cursor.fetchone()['count']
            print(f"\n2. CONSULTA CONTACTADOS:")
            print(f"   Leads huérfanos que aparecen como CONTACTADOS: {contactados_count}")

            # 3.2 Consulta de VOLVER A LLAMAR
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND TRIM(status_level_1) = 'Volver a llamar'
            """, leads_huerfanos)
            volver_count = cursor.fetchone()['count']
            print(f"\n3. CONSULTA VOLVER A LLAMAR:")
            print(f"   Leads huérfanos que aparecen como VOLVER A LLAMAR: {volver_count}")

            # 3.3 Consulta de NO INTERESADO
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND TRIM(status_level_1) = 'No Interesado'
            """, leads_huerfanos)
            no_interesado_count = cursor.fetchone()['count']
            print(f"\n4. CONSULTA NO INTERESADO:")
            print(f"   Leads huérfanos que aparecen como NO INTERESADO: {no_interesado_count}")

            # 3.4 Consulta de ÚTILES POSITIVOS
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND (TRIM(status_level_1) = 'Cita Agendada' OR TRIM(status_level_1) = 'Cita Manual')
            """, leads_huerfanos)
            utiles_count = cursor.fetchone()['count']
            print(f"\n5. CONSULTA ÚTILES POSITIVOS:")
            print(f"   Leads huérfanos que aparecen como ÚTILES POSITIVOS: {utiles_count}")

            # 3.5 Consulta de NO ÚTIL (máximo intentos)
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND call_attempts_count >= {max_attempts}
            """, leads_huerfanos)
            no_util_count = cursor.fetchone()['count']
            print(f"\n6. CONSULTA NO ÚTIL (MAX INTENTOS):")
            print(f"   Leads huérfanos que aparecen como NO ÚTIL: {no_util_count}")

            # 3.6 Consulta de OTROS ESTADOS (nueva consulta que agregué)
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND (TRIM(status_level_1) IN ('Numero erroneo', 'Interesado')
                     OR status_level_1 IS NULL
                     OR TRIM(status_level_1) = ''
                     OR TRIM(status_level_1) = 'None')
            """, leads_huerfanos)
            otros_count = cursor.fetchone()['count']
            print(f"\n7. CONSULTA OTROS ESTADOS:")
            print(f"   Leads huérfanos que aparecen como OTROS ESTADOS: {otros_count}")

            # 4. Verificación: ¿Están siendo contados en total_leads?
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
            """, leads_huerfanos)
            total_leads_count = cursor.fetchone()['count']
            print(f"\n8. VERIFICACIÓN TOTAL_LEADS:")
            print(f"   Leads huérfanos en consulta TOTAL_LEADS: {total_leads_count}")

            # 5. Análisis detallado de cada lead huérfano
            print(f"\n9. ANÁLISIS DETALLADO DE CADA LEAD HUÉRFANO:")
            cursor.execute(f"""
                SELECT
                    id, nombre, apellidos,
                    status_level_1, status_level_2,
                    call_attempts_count, lead_status,
                    (CASE
                        WHEN call_attempts_count >= {max_attempts} THEN 'NO_UTIL'
                        WHEN status_level_1 IS NULL OR TRIM(status_level_1) = '' OR TRIM(status_level_1) = 'None' THEN 'SIN_STATUS'
                        WHEN TRIM(status_level_1) = 'Volver a llamar' THEN 'VOLVER_LLAMAR'
                        WHEN TRIM(status_level_1) = 'No Interesado' THEN 'NO_INTERESADO'
                        WHEN TRIM(status_level_1) IN ('Cita Agendada', 'Cita Manual') THEN 'UTILES_POSITIVOS'
                        ELSE 'OTROS'
                    END) as categoria_calculada
                FROM leads
                WHERE id IN ({placeholders})
                ORDER BY id
            """, leads_huerfanos)

            leads_detalle = cursor.fetchall()

            categorias_contadas = {}
            for lead in leads_detalle:
                cat = lead['categoria_calculada']
                if cat not in categorias_contadas:
                    categorias_contadas[cat] = 0
                categorias_contadas[cat] += 1

                print(f"   ID {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                print(f"     Status: '{lead['status_level_1']}' | Attempts: {lead['call_attempts_count']}")
                print(f"     Lead Status: {lead['lead_status']} | Categoría: {cat}")

            print(f"\n10. RESUMEN DE CATEGORIZACIÓN:")
            for categoria, count in categorias_contadas.items():
                print(f"    {categoria}: {count} leads")

            print(f"\n11. VERIFICACIÓN DE SUMAS:")
            suma_categorias_dashboard = contactados_count + no_util_count
            print(f"    Contactados + No Útil = {contactados_count} + {no_util_count} = {suma_categorias_dashboard}")
            print(f"    Total leads huérfanos = {total_leads_count}")
            print(f"    Diferencia = {total_leads_count - suma_categorias_dashboard}")

            # 6. ¿Hay leads que NO aparecen en ninguna categoría?
            leads_sin_categoria = total_leads_count - suma_categorias_dashboard
            if leads_sin_categoria > 0:
                print(f"\n¡¡¡ PROBLEMA ENCONTRADO !!!")
                print(f"Hay {leads_sin_categoria} leads huérfanos que NO aparecen en NINGUNA categoría del dashboard")
                print(f"Estos leads están 'perdidos' en el conteo total")

    except Exception as e:
        logger.error(f"Error en verificación: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verificar_leads_en_dashboard()
#!/usr/bin/env python3
"""
Script para verificar los conteos del dashboard después de las correcciones
"""

import pymysql
import logging
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

def verificar_conteos_dashboard():
    """Verificar conteos exactos del dashboard después de correcciones"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== VERIFICACIÓN DE CONTEOS DEL DASHBOARD POST-CORRECCIÓN ===")

            # 1. Total de leads
            cursor.execute("SELECT COUNT(*) as total FROM leads")
            total_leads = cursor.fetchone()['total']
            print(f"\n1. TOTAL DE LEADS: {total_leads}")

            # 2. No interesados
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads
                WHERE status_level_1 = 'No Interesado'
            """)
            no_interesados = cursor.fetchone()['count']
            print(f"   No Interesado: {no_interesados}")

            # 3. Máximo llamadas
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads
                WHERE status_level_1 = 'Maximo llamadas'
            """)
            maximo_llamadas = cursor.fetchone()['count']
            print(f"   Maximo llamadas: {maximo_llamadas}")

            # 4. Volver a llamar (después de agregar los 26)
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads
                WHERE status_level_1 = 'Volver a llamar'
            """)
            volver_llamar = cursor.fetchone()['count']
            print(f"   Volver a llamar: {volver_llamar}")

            # 5. Útiles positivos
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads
                WHERE status_level_1 = 'Util'
            """)
            util_positivos = cursor.fetchone()['count']
            print(f"   Util (positivos): {util_positivos}")

            # 6. Número erróneo (nuevo)
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads
                WHERE status_level_1 = 'Numero erroneo'
            """)
            numero_erroneo = cursor.fetchone()['count']
            print(f"   Numero erroneo: {numero_erroneo}")

            # 7. Otros estados
            cursor.execute("""
                SELECT
                    status_level_1,
                    COUNT(*) as count
                FROM leads
                WHERE status_level_1 NOT IN ('No Interesado', 'Maximo llamadas', 'Volver a llamar', 'Util', 'Numero erroneo')
                GROUP BY status_level_1
                ORDER BY count DESC
            """)
            otros_estados = cursor.fetchall()

            total_otros = sum(row['count'] for row in otros_estados)
            print(f"   Otros estados: {total_otros}")
            if otros_estados:
                for estado in otros_estados:
                    print(f"     '{estado['status_level_1']}': {estado['count']}")

            # 8. Suma de verificación
            suma_categorias = no_interesados + maximo_llamadas + volver_llamar + util_positivos + numero_erroneo + total_otros
            print(f"\n2. SUMA DE VERIFICACIÓN:")
            print(f"   No Interesado: {no_interesados}")
            print(f"   Maximo llamadas: {maximo_llamadas}")
            print(f"   Volver a llamar: {volver_llamar}")
            print(f"   Util (positivos): {util_positivos}")
            print(f"   Numero erroneo: {numero_erroneo}")
            print(f"   Otros estados: {total_otros}")
            print(f"   --------------------------------")
            print(f"   SUMA: {suma_categorias}")
            print(f"   TOTAL LEADS: {total_leads}")
            print(f"   DIFERENCIA: {total_leads - suma_categorias}")

            if total_leads == suma_categorias:
                print(f"   ÉXITO: Todos los leads están categorizados correctamente")
            else:
                print(f"   ERROR: Faltan {total_leads - suma_categorias} leads por categorizar")

            # 9. Verificar que no hay leads huérfanos
            cursor.execute("""
                SELECT COUNT(*) as count FROM leads
                WHERE status_level_1 IS NULL
                OR status_level_1 = 'None'
                OR status_level_1 = ''
                OR TRIM(status_level_1) = ''
            """)
            huerfanos = cursor.fetchone()['count']
            print(f"\n3. LEADS HUÉRFANOS RESTANTES: {huerfanos}")

            return {
                'total': total_leads,
                'no_interesados': no_interesados,
                'maximo_llamadas': maximo_llamadas,
                'volver_llamar': volver_llamar,
                'util_positivos': util_positivos,
                'numero_erroneo': numero_erroneo,
                'otros': total_otros,
                'suma': suma_categorias,
                'huerfanos': huerfanos
            }

    except Exception as e:
        logger.error(f"Error en verificación: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    resultado = verificar_conteos_dashboard()
    if resultado:
        print(f"\nVerificación completada.")
    else:
        print("Error en verificación")
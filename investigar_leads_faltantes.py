#!/usr/bin/env python3
"""
Script para investigar dónde están los 22 leads faltantes
El usuario indica: 159 no interesados + 9 máximo llamadas + 286 volver a llamar + 24 útiles positivos = 478
Pero hay 500 leads total, faltan 22
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

def investigar_leads_faltantes():
    """Investigar exactamente dónde están clasificados todos los leads"""

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== ANÁLISIS COMPLETO DE CLASIFICACIÓN DE LEADS ===")

            # 1. Total de leads
            cursor.execute("SELECT COUNT(*) as total FROM leads")
            total_leads = cursor.fetchone()['total']
            print(f"\n1. TOTAL DE LEADS: {total_leads}")

            # 2. Obtener configuración de máximo intentos
            cursor.execute("SELECT config_value FROM scheduler_config WHERE config_key = 'max_attempts'")
            row_max = cursor.fetchone()
            max_attempts = int(row_max['config_value']) if row_max else 6
            print(f"   Máximo intentos configurado: {max_attempts}")

            # 3. Análisis por status_level_1 (estado principal)
            print(f"\n2. ANÁLISIS POR STATUS_LEVEL_1:")
            cursor.execute("""
                SELECT
                    COALESCE(NULLIF(TRIM(status_level_1), ''), 'NULL/VACÍO') as estado,
                    COUNT(*) as count
                FROM leads
                GROUP BY COALESCE(NULLIF(TRIM(status_level_1), ''), 'NULL/VACÍO')
                ORDER BY count DESC
            """)

            status_breakdown = cursor.fetchall()
            suma_status = 0

            for status in status_breakdown:
                print(f"   {status['estado']}: {status['count']}")
                suma_status += status['count']

            print(f"   TOTAL verificado: {suma_status}")

            # 4. Análisis específico de las categorías mencionadas por el usuario
            print(f"\n3. VERIFICACIÓN DE LAS CATEGORÍAS MENCIONADAS:")

            # No interesados
            cursor.execute("SELECT COUNT(*) as count FROM leads WHERE TRIM(status_level_1) = 'No Interesado'")
            no_interesados = cursor.fetchone()['count']
            print(f"   No Interesado: {no_interesados}")

            # Útiles positivos (Cita Agendada o Cita Manual)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE TRIM(status_level_1) IN ('Cita Agendada', 'Cita Manual')
            """)
            utiles_positivos = cursor.fetchone()['count']
            print(f"   Útiles Positivos (Cita Agendada/Manual): {utiles_positivos}")

            # Volver a llamar
            cursor.execute("SELECT COUNT(*) as count FROM leads WHERE TRIM(status_level_1) = 'Volver a llamar'")
            volver_llamar = cursor.fetchone()['count']
            print(f"   Volver a llamar: {volver_llamar}")

            # Máximo intentos alcanzado
            cursor.execute(f"SELECT COUNT(*) as count FROM leads WHERE call_attempts_count >= {max_attempts}")
            max_intentos = cursor.fetchone()['count']
            print(f"   Máximo intentos alcanzado: {max_intentos}")

            # 5. Suma de las categorías mencionadas
            suma_categorias = no_interesados + utiles_positivos + volver_llamar + max_intentos
            print(f"\n4. SUMA DE CATEGORÍAS MENCIONADAS:")
            print(f"   {no_interesados} + {utiles_positivos} + {volver_llamar} + {max_intentos} = {suma_categorias}")
            print(f"   Diferencia con total: {total_leads} - {suma_categorias} = {total_leads - suma_categorias}")

            # 6. Buscar los leads "faltantes" - aquellos que no están en las 4 categorías principales
            print(f"\n5. ANÁLISIS DE LEADS FALTANTES:")
            cursor.execute(f"""
                SELECT
                    id, nombre, apellidos, telefono,
                    status_level_1, status_level_2,
                    call_attempts_count, lead_status,
                    call_status, selected_for_calling
                FROM leads
                WHERE
                    (TRIM(status_level_1) NOT IN ('No Interesado', 'Cita Agendada', 'Cita Manual', 'Volver a llamar')
                     OR status_level_1 IS NULL OR TRIM(status_level_1) = '')
                    AND call_attempts_count < {max_attempts}
                ORDER BY id
            """)

            leads_faltantes = cursor.fetchall()
            print(f"   Leads que no están en las 4 categorías principales: {len(leads_faltantes)}")

            if leads_faltantes:
                print(f"\n   DETALLE DE LEADS FALTANTES:")
                for lead in leads_faltantes:
                    print(f"   ID {lead['id']}: {lead['nombre']} {lead['apellidos']}")
                    print(f"     Teléfono: {lead['telefono']}")
                    print(f"     Status L1: '{lead['status_level_1']}' | L2: '{lead['status_level_2']}'")
                    print(f"     Attempts: {lead['call_attempts_count']} | Lead Status: {lead['lead_status']}")
                    print(f"     Call Status: {lead['call_status']} | Selected: {lead['selected_for_calling']}")
                    print("     ---")

            # 7. Análisis de leads con status_level_1 vacío o NULL
            print(f"\n6. LEADS SIN STATUS_LEVEL_1 (NULL/VACÍO):")
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM leads
                WHERE status_level_1 IS NULL OR TRIM(status_level_1) = ''
            """)
            sin_status = cursor.fetchone()['count']
            print(f"   Leads sin status_level_1: {sin_status}")

            if sin_status > 0:
                cursor.execute(f"""
                    SELECT
                        call_attempts_count,
                        COUNT(*) as count
                    FROM leads
                    WHERE status_level_1 IS NULL OR TRIM(status_level_1) = ''
                    GROUP BY call_attempts_count
                    ORDER BY call_attempts_count
                """)
                sin_status_desglose = cursor.fetchall()
                print(f"   Desglose por intentos de llamada:")
                for item in sin_status_desglose:
                    attempts = item['call_attempts_count']
                    count = item['count']
                    categoria = "Máximo alcanzado" if attempts >= max_attempts else "Activos"
                    print(f"     {attempts} intentos: {count} leads ({categoria})")

            # 8. Verificación final con cálculo correcto
            print(f"\n7. VERIFICACIÓN FINAL:")
            sin_status_activos = 0
            sin_status_max = 0

            if sin_status > 0:
                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM leads
                    WHERE (status_level_1 IS NULL OR TRIM(status_level_1) = '')
                    AND call_attempts_count < {max_attempts}
                """)
                sin_status_activos = cursor.fetchone()['count']

                cursor.execute(f"""
                    SELECT COUNT(*) as count
                    FROM leads
                    WHERE (status_level_1 IS NULL OR TRIM(status_level_1) = '')
                    AND call_attempts_count >= {max_attempts}
                """)
                sin_status_max = cursor.fetchone()['count']

            # Recalcular con la categorización correcta
            max_intentos_total = max_intentos  # Ya incluye los sin status
            suma_correcta = no_interesados + utiles_positivos + volver_llamar + sin_status_activos

            print(f"   Categorización correcta:")
            print(f"     No Interesado: {no_interesados}")
            print(f"     Útiles Positivos: {utiles_positivos}")
            print(f"     Volver a llamar: {volver_llamar}")
            print(f"     Sin status (activos): {sin_status_activos}")
            print(f"     Máximo intentos (total): {max_intentos_total}")
            print(f"   SUMA: {suma_correcta} + {max_intentos_total} = {suma_correcta + max_intentos_total}")
            print(f"   Diferencia: {total_leads} - {suma_correcta + max_intentos_total} = {total_leads - (suma_correcta + max_intentos_total)}")

    except Exception as e:
        logger.error(f"Error en investigación: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    investigar_leads_faltantes()
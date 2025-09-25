#!/usr/bin/env python3
"""
Script para aplicar las correcciones SQL a los 31 leads huérfanos
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

def aplicar_correcciones():
    """Aplicar las correcciones definitivas a los 31 leads huérfanos"""

    # Correcciones exactas basadas en análisis
    correcciones = [
        # Leads con 2+ Outcome 6 → "Numero erroneo"
        (2108, "Numero erroneo", "Fallo múltiple"),
        (2147, "Numero erroneo", "Fallo múltiple"),
        (2157, "Numero erroneo", "Fallo múltiple"),
        (2264, "Numero erroneo", "Fallo múltiple"),
        (2280, "Numero erroneo", "Fallo múltiple"),

        # Leads con 1 Outcome 6 → "Volver a llamar"
        (1971, "Volver a llamar", "Fallo centralita"),
        (1989, "Volver a llamar", "Fallo centralita"),
        (2002, "Volver a llamar", "Fallo centralita"),
        (2092, "Volver a llamar", "Fallo centralita"),
        (2094, "Volver a llamar", "Fallo centralita"),
        (2098, "Volver a llamar", "Fallo centralita"),
        (2186, "Volver a llamar", "Fallo centralita"),
        (2315, "Volver a llamar", "Fallo centralita"),
        (2323, "Volver a llamar", "Fallo centralita"),
        (2388, "Volver a llamar", "Fallo centralita"),
        (2405, "Volver a llamar", "Fallo centralita"),

        # Leads solo con no-contacto (4,5,7) → "Volver a llamar"
        (1985, "Volver a llamar", "no disponible cliente"),
        (2000, "Volver a llamar", "no disponible cliente"),
        (2005, "Volver a llamar", "buzón"),
        (2072, "Volver a llamar", "no disponible cliente"),
        (2090, "Volver a llamar", "no disponible cliente"),
        (2132, "Volver a llamar", "no disponible cliente"),
        (2162, "Volver a llamar", "no disponible cliente"),
        (2243, "Volver a llamar", "buzón"),
        (2261, "Volver a llamar", "no disponible cliente"),
        (2273, "Volver a llamar", "no disponible cliente"),
        (2328, "Volver a llamar", "no disponible cliente"),
        (2372, "Volver a llamar", "no disponible cliente"),
        (2399, "Volver a llamar", "buzón"),
        (2407, "Volver a llamar", "no disponible cliente"),
        (2422, "Volver a llamar", "buzón"),
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("=== APLICANDO CORRECCIONES A LEADS HUÉRFANOS ===")

            # Mostrar estado antes de la corrección
            lead_ids = [str(c[0]) for c in correcciones]
            placeholders = ','.join(['%s'] * len(lead_ids))

            print(f"\n1. ESTADO ANTES DE LAS CORRECCIONES:")
            cursor.execute(f"""
                SELECT
                    status_level_1,
                    COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                GROUP BY status_level_1
            """, lead_ids)

            estado_antes = cursor.fetchall()
            for estado in estado_antes:
                print(f"   status_level_1 = '{estado['status_level_1']}': {estado['count']} leads")

            # Aplicar correcciones una por una
            print(f"\n2. APLICANDO CORRECCIONES:")
            correcciones_exitosas = 0
            correcciones_fallidas = 0

            for lead_id, status1, status2 in correcciones:
                try:
                    # Verificar que el lead existe
                    cursor.execute("SELECT nombre, apellidos, status_level_1 FROM leads WHERE id = %s", (lead_id,))
                    lead_actual = cursor.fetchone()

                    if not lead_actual:
                        print(f"   ERROR Lead {lead_id}: No encontrado")
                        correcciones_fallidas += 1
                        continue

                    # Aplicar corrección
                    cursor.execute("""
                        UPDATE leads
                        SET status_level_1 = %s, status_level_2 = %s
                        WHERE id = %s
                    """, (status1, status2, lead_id))

                    print(f"   OK Lead {lead_id} ({lead_actual['nombre']} {lead_actual['apellidos']}): '{lead_actual['status_level_1']}' -> '{status1}'")
                    correcciones_exitosas += 1

                except Exception as e:
                    print(f"   ERROR Lead {lead_id}: {e}")
                    correcciones_fallidas += 1

            # Confirmar cambios
            conn.commit()

            # Mostrar estado después de las correcciones
            print(f"\n3. ESTADO DESPUÉS DE LAS CORRECCIONES:")
            cursor.execute(f"""
                SELECT
                    status_level_1,
                    COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                GROUP BY status_level_1
            """, lead_ids)

            estado_despues = cursor.fetchall()
            for estado in estado_despues:
                print(f"   status_level_1 = '{estado['status_level_1']}': {estado['count']} leads")

            # Verificar que ya no hay leads con status NULL/None
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM leads
                WHERE id IN ({placeholders})
                AND (status_level_1 IS NULL OR status_level_1 = 'None')
            """, lead_ids)

            leads_pendientes = cursor.fetchone()['count']

            print(f"\n4. RESUMEN:")
            print(f"   Correcciones exitosas: {correcciones_exitosas}")
            print(f"   Correcciones fallidas: {correcciones_fallidas}")
            print(f"   Leads con status NULL/None restantes: {leads_pendientes}")

            if leads_pendientes == 0:
                print("   🎉 ÉXITO: Todos los leads huérfanos han sido corregidos")
            else:
                print(f"   ⚠️ ATENCIÓN: Quedan {leads_pendientes} leads sin corregir")

            return correcciones_exitosas

    except Exception as e:
        logger.error(f"Error aplicando correcciones: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    resultado = aplicar_correcciones()
    print(f"\nProceso completado. Leads corregidos: {resultado}")
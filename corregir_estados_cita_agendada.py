#!/usr/bin/env python3
"""
Corrige los estados de Cita Agendada según el criterio correcto:
1. Leads con cita real (campo 'cita' != NULL) -> 'Cita Agendada'
2. Leads con fecha_minima_reserva != NULL -> 'Cita Agendada'
"""

import pymysql
from datetime import datetime

# Configuracion de Railway
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    return pymysql.connect(**RAILWAY_CONFIG)

def corregir_estados_cita_agendada():
    """Corrige los estados de cita agendada según el criterio correcto"""

    print("=== CORRECCION ESTADOS 'CITA AGENDADA' ===")
    print(f"Fecha/hora: {datetime.now()}")
    print()

    conn = get_railway_connection()
    cursor = conn.cursor()

    try:
        # 1. Estado inicial
        print("1. ESTADO INICIAL:")

        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Cita Agendada'
        """)
        inicial_cita_agendada = cursor.fetchone()[0]
        print(f"   Leads con 'Cita Agendada': {inicial_cita_agendada}")

        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND cita IS NOT NULL
        """)
        con_cita_real = cursor.fetchone()[0]
        print(f"   Leads con cita real (campo 'cita'): {con_cita_real}")

        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND fecha_minima_reserva IS NOT NULL
        """)
        con_fecha_minima = cursor.fetchone()[0]
        print(f"   Leads con fecha_minima_reserva: {con_fecha_minima}")

        print()

        # 2. Análisis detallado de lo que necesita corrección
        print("2. ANALISIS DE CORRECCIONES NECESARIAS:")

        # Leads con cita real pero NO en "Cita Agendada"
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND cita IS NOT NULL
            AND status_level_1 != 'Cita Agendada'
        """)
        cita_sin_estado = cursor.fetchone()[0]
        print(f"   Leads con cita real pero NO 'Cita Agendada': {cita_sin_estado}")

        if cita_sin_estado > 0:
            cursor.execute("""
                SELECT id, nombre, telefono, status_level_1, cita, hora_cita
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND cita IS NOT NULL
                AND status_level_1 != 'Cita Agendada'
                ORDER BY cita
            """)
            ejemplos_cita = cursor.fetchall()

            print("     Ejemplos a corregir:")
            for id, nombre, tel, status1, cita, hora in ejemplos_cita:
                hora_str = str(hora) if hora else 'sin hora'
                print(f"       Lead {id}: {nombre} ({tel})")
                print(f"         Actual: '{status1}' -> Debe ser: 'Cita Agendada'")
                print(f"         Cita: {cita} {hora_str}")

        # Leads con fecha_minima_reserva pero NO en "Cita Agendada"
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND fecha_minima_reserva IS NOT NULL
            AND status_level_1 != 'Cita Agendada'
        """)
        fecha_minima_sin_estado = cursor.fetchone()[0]
        print(f"   Leads con fecha_minima_reserva pero NO 'Cita Agendada': {fecha_minima_sin_estado}")

        if fecha_minima_sin_estado > 0:
            cursor.execute("""
                SELECT id, nombre, telefono, status_level_1, fecha_minima_reserva
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND fecha_minima_reserva IS NOT NULL
                AND status_level_1 != 'Cita Agendada'
                LIMIT 5
            """)
            ejemplos_fecha_minima = cursor.fetchall()

            print("     Ejemplos con fecha_minima_reserva a corregir:")
            for id, nombre, tel, status1, fecha_min in ejemplos_fecha_minima:
                print(f"       Lead {id}: {nombre} ({tel})")
                print(f"         Actual: '{status1}' -> Debe ser: 'Cita Agendada'")
                print(f"         fecha_minima_reserva: {fecha_min}")

        # Verificar leads marcados como "Cita Agendada" que NO tienen ni cita ni fecha_minima
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Cita Agendada'
            AND cita IS NULL
            AND fecha_minima_reserva IS NULL
        """)
        cita_agendada_sin_justificacion = cursor.fetchone()[0]
        print(f"   Leads 'Cita Agendada' SIN cita ni fecha_minima: {cita_agendada_sin_justificacion}")

        if cita_agendada_sin_justificacion > 0:
            cursor.execute("""
                SELECT id, nombre, telefono, status_level_2
                FROM leads
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND status_level_1 = 'Cita Agendada'
                AND cita IS NULL
                AND fecha_minima_reserva IS NULL
            """)
            sin_justificacion = cursor.fetchall()

            print("     Leads 'Cita Agendada' sin justificacion:")
            for id, nombre, tel, status2 in sin_justificacion:
                print(f"       Lead {id}: {nombre} ({tel}), status_level_2: '{status2}'")

        print()

        # 3. Ejecutar correcciones automaticamente
        print("3. EJECUTANDO CORRECCIONES:")

        # Corrección 1: Leads con cita real -> 'Cita Agendada'
        if cita_sin_estado > 0:
            print("   Corrigiendo leads con cita real...")
            cursor.execute("""
                UPDATE leads
                SET status_level_1 = 'Cita Agendada',
                    updated_at = NOW()
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND cita IS NOT NULL
                AND status_level_1 != 'Cita Agendada'
            """)
            corregidos_cita = cursor.rowcount
            print(f"   [OK] {corregidos_cita} leads corregidos (tenian cita real)")

        # Corrección 2: Leads con fecha_minima_reserva -> 'Cita Agendada'
        if fecha_minima_sin_estado > 0:
            print("   Corrigiendo leads con fecha_minima_reserva...")
            cursor.execute("""
                UPDATE leads
                SET status_level_1 = 'Cita Agendada',
                    updated_at = NOW()
                WHERE origen_archivo = 'SEGURCAIXA_JULIO'
                AND fecha_minima_reserva IS NOT NULL
                AND status_level_1 != 'Cita Agendada'
            """)
            corregidos_fecha = cursor.rowcount
            print(f"   [OK] {corregidos_fecha} leads corregidos (tenian fecha_minima_reserva)")

        # Commit cambios
        conn.commit()

        # 4. Estado final
        print()
        print("4. ESTADO FINAL:")

        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Cita Agendada'
        """)
        final_cita_agendada = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Volver a llamar'
        """)
        final_volver_llamar = cursor.fetchone()[0]

        print(f"   Leads con 'Cita Agendada': {final_cita_agendada} (antes: {inicial_cita_agendada})")
        print(f"   Leads con 'Volver a llamar': {final_volver_llamar}")

        # Verificación final
        cursor.execute("""
            SELECT COUNT(*) FROM leads
            WHERE origen_archivo = 'SEGURCAIXA_JULIO'
            AND status_level_1 = 'Cita Agendada'
            AND (cita IS NOT NULL OR fecha_minima_reserva IS NOT NULL)
        """)
        justificados = cursor.fetchone()[0]

        print(f"   Leads 'Cita Agendada' con justificacion: {justificados}/{final_cita_agendada}")

        if justificados == final_cita_agendada:
            print("   [OK] TODOS los 'Cita Agendada' tienen justificacion correcta")
        else:
            print(f"   [WARNING] {final_cita_agendada - justificados} leads 'Cita Agendada' sin justificacion")

        print()
        print("RESUMEN DE CAMBIOS:")
        total_corregidos = (corregidos_cita if cita_sin_estado > 0 else 0) + (corregidos_fecha if fecha_minima_sin_estado > 0 else 0)
        print(f"  Total leads corregidos: {total_corregidos}")
        print(f"  'Cita Agendada' final: {final_cita_agendada}")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if corregir_estados_cita_agendada():
        print()
        print("=" * 60)
        print("[EXITO] ESTADOS CORREGIDOS CORRECTAMENTE")
        print("Los leads ahora reflejan el criterio correcto:")
        print("- Cita real (campo 'cita') -> 'Cita Agendada'")
        print("- fecha_minima_reserva -> 'Cita Agendada'")
    else:
        print()
        print("[ERROR] La correccion fallo")
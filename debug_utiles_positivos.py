#!/usr/bin/env python3
"""
Script para investigar la discrepancia en utiles positivos del dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_connection

def investigar_utiles_positivos():
    """Investiga por que solo aparecen 4 utiles positivos cuando hay mas citas"""

    conn = get_connection()
    if not conn:
        print("ERROR: No se pudo conectar a la base de datos")
        return

    try:
        cursor = conn.cursor(dictionary=True)

        print("INVESTIGANDO UTILES POSITIVOS - ARCHIVO SEPTIEMBRE")
        print("=" * 60)

        # 1. Verificar archivos disponibles
        print("\n1. ARCHIVOS DISPONIBLES:")
        cursor.execute("SELECT nombre_archivo, total_registros FROM archivos_origen WHERE activo = 1 ORDER BY nombre_archivo")
        archivos = cursor.fetchall()
        for archivo in archivos:
            print(f"   {archivo['nombre_archivo']}: {archivo['total_registros']} registros")

        # 2. Buscar archivo de septiembre
        archivos_septiembre = []
        for a in archivos:
            nombre_lower = a['nombre_archivo'].lower()
            if 'septiembre' in nombre_lower or 'sep' in nombre_lower or '09' in nombre_lower:
                archivos_septiembre.append(a)

        if not archivos_septiembre:
            print("\nNo se encontro archivo especifico de septiembre. Usando el primero disponible:")
            archivo_septiembre = archivos[0]['nombre_archivo'] if archivos else None
        else:
            archivo_septiembre = archivos_septiembre[0]['nombre_archivo']
            print(f"\nArchivo de septiembre encontrado: {archivo_septiembre}")

        if not archivo_septiembre:
            print("ERROR: No hay archivos disponibles")
            return

        # 3. Analizar registros del archivo
        print(f"\n2. ANALISIS DETALLADO - {archivo_septiembre}")
        print("-" * 50)

        # Total de registros del archivo
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE origen_archivo = %s", (archivo_septiembre,))
        total_archivo = cursor.fetchone()['total']
        print(f"Total registros en {archivo_septiembre}: {total_archivo}")

        # Citas agendadas (status_level_1 = 'Cita Agendada')
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s AND TRIM(status_level_1) = 'Cita Agendada'
        """, (archivo_septiembre,))
        citas_agendadas = cursor.fetchone()['count']
        print(f"Citas agendadas (status_level_1): {citas_agendadas}")

        # Citas manuales (cita IS NOT NULL)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s AND cita IS NOT NULL
        """, (archivo_septiembre,))
        citas_manuales = cursor.fetchone()['count']
        print(f"Citas manuales (cita IS NOT NULL): {citas_manuales}")

        # Solapamiento - registros que tienen AMBOS
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
            AND cita IS NOT NULL
        """, (archivo_septiembre,))
        solapamiento = cursor.fetchone()['count']
        print(f"Solapamiento (ambos campos): {solapamiento}")

        # Utiles positivos segun nueva logica
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL)
        """, (archivo_septiembre,))
        utiles_positivos_nuevo = cursor.fetchone()['count']
        print(f"Utiles positivos (nueva logica): {utiles_positivos_nuevo}")

        # 4. Mostrar algunos registros de ejemplo
        print(f"\n3. EJEMPLOS DE REGISTROS")
        print("-" * 50)

        # Registros con citas agendadas
        print("CITAS AGENDADAS (primeras 3):")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s AND TRIM(status_level_1) = 'Cita Agendada'
            LIMIT 3
        """, (archivo_septiembre,))
        ejemplos_agendadas = cursor.fetchall()

        for registro in ejemplos_agendadas:
            print(f"  {registro['nombre']} {registro['apellidos']} - Tel: {registro['telefono']}")
            print(f"    Status: {registro['status_level_1']} / {registro['status_level_2']}")
            print(f"    Cita manual: {registro['cita']}")

        # Registros con citas manuales pero sin status agendada
        print("\nCITAS MANUALES SIN STATUS AGENDADA (primeras 3):")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s
            AND cita IS NOT NULL
            AND (TRIM(status_level_1) != 'Cita Agendada' OR status_level_1 IS NULL)
            LIMIT 3
        """, (archivo_septiembre,))
        ejemplos_manuales = cursor.fetchall()

        for registro in ejemplos_manuales:
            print(f"  {registro['nombre']} {registro['apellidos']} - Tel: {registro['telefono']}")
            print(f"    Status: {registro['status_level_1']} / {registro['status_level_2']}")
            print(f"    Cita manual: {registro['cita']}")

        if not ejemplos_manuales:
            print("  No hay citas manuales sin status 'Cita Agendada'")

        # 5. Simulacion de consulta del dashboard
        print(f"\n4. SIMULACION CONSULTA DASHBOARD")
        print("-" * 50)

        cursor.execute("""
            SELECT
                IFNULL(SUM(CASE WHEN (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL) THEN 1 ELSE 0 END), 0) AS utiles_positivos
            FROM leads
            WHERE origen_archivo = %s
        """, (archivo_septiembre,))

        dashboard_result = cursor.fetchone()
        print(f"Dashboard deberia mostrar utiles positivos: {dashboard_result['utiles_positivos']}")

        print(f"\nCONCLUSION:")
        print(f"Matematicamente: {citas_agendadas} + {citas_manuales} - {solapamiento} = {citas_agendadas + citas_manuales - solapamiento}")
        print(f"Consulta OR: {utiles_positivos_nuevo}")

        if dashboard_result['utiles_positivos'] == 4:
            print("PROBLEMA: El dashboard sigue mostrando solo 4")
        else:
            print(f"SOLUCIONADO: El dashboard ahora muestra {dashboard_result['utiles_positivos']}")

    except Exception as e:
        print(f"Error durante la investigacion: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    investigar_utiles_positivos()
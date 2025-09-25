#!/usr/bin/env python3
"""
Script para verificar directamente en Railway los datos de utiles positivos
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def conectar_railway():
    """Conectar directamente a Railway"""
    try:
        config = {
            'host': 'ballast.proxy.rlwy.net',
            'port': 11616,
            'user': 'root',
            'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
            'database': 'railway',
            'ssl_disabled': True,
            'autocommit': True,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'auth_plugin': 'mysql_native_password'
        }

        conn = mysql.connector.connect(**config)
        return conn
    except Exception as e:
        print(f"Error conectando a Railway: {e}")
        return None

def investigar_utiles_positivos_railway():
    """Investigar utiles positivos en Railway"""

    conn = conectar_railway()
    if not conn:
        print("No se pudo conectar a Railway")
        return

    try:
        cursor = conn.cursor(dictionary=True)

        print("INVESTIGACION UTILES POSITIVOS - RAILWAY")
        print("=" * 60)

        # 1. Verificar archivos disponibles
        print("\n1. ARCHIVOS DISPONIBLES EN RAILWAY:")
        cursor.execute("SELECT nombre_archivo, total_registros FROM archivos_origen WHERE activo = 1 ORDER BY nombre_archivo")
        archivos = cursor.fetchall()

        archivo_septiembre = None

        for archivo in archivos:
            print(f"   {archivo['nombre_archivo']}: {archivo['total_registros']} registros")
            # Buscar archivo de septiembre
            nombre_lower = archivo['nombre_archivo'].lower()
            if any(x in nombre_lower for x in ['septiembre', 'sep', '09-']):
                archivo_septiembre = archivo['nombre_archivo']
                print(f"   --> ARCHIVO SEPTIEMBRE IDENTIFICADO: {archivo_septiembre}")

        if not archivo_septiembre:
            print("\nNo se encontro archivo de septiembre especifico.")
            print("Usando el primer archivo disponible como ejemplo:")
            archivo_septiembre = archivos[0]['nombre_archivo'] if archivos else None
            print(f"   --> USANDO: {archivo_septiembre}")

        if not archivo_septiembre:
            print("No hay archivos disponibles")
            return

        # 2. Analizar datos del archivo de septiembre
        print(f"\n2. ANALISIS DETALLADO - {archivo_septiembre}")
        print("-" * 50)

        # Total registros
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE origen_archivo = %s", (archivo_septiembre,))
        total = cursor.fetchone()['total']
        print(f"Total registros: {total}")

        # Citas agendadas
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
        """, (archivo_septiembre,))
        citas_agendadas = cursor.fetchone()['count']
        print(f"Citas agendadas (status_level_1='Cita Agendada'): {citas_agendadas}")

        # Citas manuales
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND cita IS NOT NULL
            AND cita != ''
        """, (archivo_septiembre,))
        citas_manuales = cursor.fetchone()['count']
        print(f"Citas manuales (cita IS NOT NULL y no vacia): {citas_manuales}")

        # Solapamiento
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
            AND cita IS NOT NULL
            AND cita != ''
        """, (archivo_septiembre,))
        solapamiento = cursor.fetchone()['count']
        print(f"Registros con AMBOS (solapamiento): {solapamiento}")

        # Utiles positivos nueva formula
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (TRIM(status_level_1) = 'Cita Agendada' OR (cita IS NOT NULL AND cita != ''))
        """, (archivo_septiembre,))
        utiles_positivos = cursor.fetchone()['count']
        print(f"UTILES POSITIVOS (formula corregida): {utiles_positivos}")

        # 3. Mostrar ejemplos
        print(f"\n3. EJEMPLOS DE DATOS")
        print("-" * 50)

        print("CITAS AGENDADAS (primeras 3):")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
            LIMIT 3
        """, (archivo_septiembre,))

        for row in cursor.fetchall():
            print(f"  {row['nombre']} {row['apellidos']} - {row['telefono']}")
            print(f"    Status: {row['status_level_1']} / {row['status_level_2']}")
            print(f"    Cita manual: {row['cita']}")
            print()

        print("CITAS MANUALES SIN STATUS AGENDADA (primeras 3):")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s
            AND (cita IS NOT NULL AND cita != '')
            AND (TRIM(status_level_1) != 'Cita Agendada' OR status_level_1 IS NULL)
            LIMIT 3
        """, (archivo_septiembre,))

        ejemplos_solo_manual = cursor.fetchall()
        if ejemplos_solo_manual:
            for row in ejemplos_solo_manual:
                print(f"  {row['nombre']} {row['apellidos']} - {row['telefono']}")
                print(f"    Status: {row['status_level_1']} / {row['status_level_2']}")
                print(f"    Cita manual: {row['cita']}")
                print()
        else:
            print("  No hay citas manuales sin status 'Cita Agendada'")

        # 4. Verificar exactamente que esta pasando con la consulta del dashboard
        print(f"\n4. SIMULACION EXACTA CONSULTA DASHBOARD")
        print("-" * 50)

        cursor.execute("""
            SELECT
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Sin Pack' THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Con Pack' THEN 1 ELSE 0 END), 0) AS cita_con_pack,
                IFNULL(SUM(CASE WHEN (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL) THEN 1 ELSE 0 END), 0) AS utiles_positivos
            FROM leads
            WHERE origen_archivo = %s
        """, (archivo_septiembre,))

        dashboard_data = cursor.fetchone()
        print(f"Dashboard deberia mostrar:")
        print(f"  Citas sin pack: {dashboard_data['cita_sin_pack']}")
        print(f"  Citas con pack: {dashboard_data['cita_con_pack']}")
        print(f"  UTILES POSITIVOS: {dashboard_data['utiles_positivos']}")

        # 5. Analisis del problema
        print(f"\n5. DIAGNOSTICO")
        print("-" * 50)

        if dashboard_data['utiles_positivos'] == 4:
            print("PROBLEMA CONFIRMADO: Solo 4 utiles positivos")
            print("Posibles causas:")
            print("1. Muy pocas citas manuales reales en este archivo")
            print("2. Las citas manuales son cadenas vacias o NULL")
            print("3. Problema con el filtro del archivo de septiembre")

            # Verificar valores NULL vs vacios en campo cita
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN cita IS NULL THEN 1 ELSE 0 END) as cita_null,
                    SUM(CASE WHEN cita = '' THEN 1 ELSE 0 END) as cita_vacia,
                    SUM(CASE WHEN cita IS NOT NULL AND cita != '' THEN 1 ELSE 0 END) as cita_valida
                FROM leads
                WHERE origen_archivo = %s
            """, (archivo_septiembre,))

            cita_stats = cursor.fetchone()
            print(f"\nEstadisticas campo 'cita':")
            print(f"  NULL: {cita_stats['cita_null']}")
            print(f"  Vacia (''): {cita_stats['cita_vacia']}")
            print(f"  Con valor: {cita_stats['cita_valida']}")

        else:
            print(f"SOLUCIONADO: Ahora muestra {dashboard_data['utiles_positivos']} utiles positivos")
            print("El cambio en el codigo ha funcionado correctamente")

    except Exception as e:
        print(f"Error durante la investigacion: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    investigar_utiles_positivos_railway()
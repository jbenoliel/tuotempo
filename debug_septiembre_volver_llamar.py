#!/usr/bin/env python3
"""
Script para debuggear el problema con la selección de leads
en estado "Volver a llamar" para el archivo de septiembre
"""

import os
import sys
from db import get_connection

def debug_septiembre_leads():
    """Analizar leads de septiembre"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        print("=== ANALISIS DE LEADS DE SEPTIEMBRE ===")

        # 1. Total leads en archivo septiembre
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%'
        """)
        total_septiembre = cursor.fetchone()['total']
        print(f"Total leads en archivo de septiembre: {total_septiembre}")

        # 2. Leads con estado "Volver a llamar" en septiembre
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE (origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%')
            AND TRIM(status_level_1) = 'Volver a llamar'
        """)
        volver_llamar_total = cursor.fetchone()['total']
        print(f"Leads con 'Volver a llamar' en septiembre: {volver_llamar_total}")

        # 3. Leads que cumplen TODAS las condiciones del filtro (como en el backend)
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE (origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%')
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (status_level_2 IS NULL OR TRIM(status_level_2) != 'Cita programada')
        """)
        volver_llamar_filtrado = cursor.fetchone()['total']
        print(f"Leads validos para seleccion (con todos los filtros): {volver_llamar_filtrado}")

        # 4. Verificar archivos de origen exactos
        cursor.execute("""
            SELECT DISTINCT origen_archivo, COUNT(*) as total
            FROM leads
            WHERE (origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%')
            GROUP BY origen_archivo
        """)
        archivos = cursor.fetchall()
        print(f"\nArchivos de septiembre encontrados:")
        for archivo in archivos:
            print(f"   - {archivo['origen_archivo']}: {archivo['total']} leads")

        # 5. Verificar estados exactos
        cursor.execute("""
            SELECT DISTINCT TRIM(status_level_1) as estado, COUNT(*) as total
            FROM leads
            WHERE (origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%')
            GROUP BY TRIM(status_level_1)
            ORDER BY total DESC
        """)
        estados = cursor.fetchall()
        print(f"\nEstados en septiembre:")
        for estado in estados:
            print(f"   - '{estado['estado']}': {estado['total']} leads")

        # 6. Verificar leads cerrados
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE (origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%')
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND TRIM(lead_status) != 'open' AND lead_status IS NOT NULL
        """)
        cerrados = cursor.fetchone()['total']
        print(f"Leads 'Volver a llamar' cerrados en septiembre: {cerrados}")

        # 7. Verificar leads con citas programadas
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE (origen_archivo LIKE '%septiembre%' OR origen_archivo LIKE '%Septiembre%')
            AND TRIM(status_level_1) = 'Volver a llamar'
            AND TRIM(status_level_2) = 'Cita programada'
        """)
        citas = cursor.fetchone()['total']
        print(f"Leads 'Volver a llamar' con cita programada en septiembre: {citas}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_septiembre_leads()
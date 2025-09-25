#!/usr/bin/env python3
"""
Script para comparar las consultas del dashboard vs calls-manager
para los leads de septiembre con estado "Volver a llamar"
"""

import os
import sys
from db import get_connection

def comparar_consultas():
    """Comparar consultas del dashboard vs calls-manager"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        print("=== COMPARACIÓN DE CONSULTAS SEPTIEMBRE - VOLVER A LLAMAR ===")

        # 1. Consulta BÁSICA - Sin filtros especiales (como dashboard original)
        print("\n1. CONSULTA BÁSICA (estilo dashboard):")
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%' OR origen_archivo LIKE '%septiembre%')
        """)
        resultado_basico = cursor.fetchone()['total']
        print(f"   Resultado: {resultado_basico} leads")

        # 2. Consulta CALLS-MANAGER ACTUAL - Con filtros de negocio
        print("\n2. CONSULTA CALLS-MANAGER (con filtros de negocio):")
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (lead_status IS NULL OR TRIM(lead_status) = 'open')
            AND (TRIM(origen_archivo) LIKE '%Septiembre%' OR origen_archivo LIKE '%septiembre%')
        """)
        resultado_calls_manager = cursor.fetchone()['total']
        print(f"   Resultado: {resultado_calls_manager} leads")

        # 3. Ver la diferencia específica - leads cerrados
        print("\n3. DIFERENCIA - Leads CERRADOS:")
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND TRIM(lead_status) != 'open' AND lead_status IS NOT NULL
            AND (TRIM(origen_archivo) LIKE '%Septiembre%' OR origen_archivo LIKE '%septiembre%')
        """)
        leads_cerrados = cursor.fetchone()['total']
        print(f"   Leads 'Volver a llamar' CERRADOS en Septiembre: {leads_cerrados}")

        # 4. Verificar nombres exactos de archivos
        print("\n4. NOMBRES EXACTOS DE ARCHIVOS CON 'SEPTIEMBRE':")
        cursor.execute("""
            SELECT DISTINCT origen_archivo, COUNT(*) as total_leads,
                   SUM(CASE WHEN TRIM(status_level_1) = 'Volver a llamar' THEN 1 ELSE 0 END) as volver_llamar
            FROM leads
            WHERE (TRIM(origen_archivo) LIKE '%Septiembre%' OR origen_archivo LIKE '%septiembre%')
            GROUP BY origen_archivo
            ORDER BY total_leads DESC
        """)
        archivos = cursor.fetchall()
        for archivo in archivos:
            print(f"   - '{archivo['origen_archivo']}': {archivo['total_leads']} total, {archivo['volver_llamar']} 'Volver a llamar'")

        # 5. Verificar lead_status de los que tienen "Volver a llamar" en Septiembre
        print("\n5. ESTADOS DE LEAD_STATUS PARA 'VOLVER A LLAMAR' EN SEPTIEMBRE:")
        cursor.execute("""
            SELECT lead_status, COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%' OR origen_archivo LIKE '%septiembre%')
            GROUP BY lead_status
            ORDER BY total DESC
        """)
        estados_lead = cursor.fetchall()
        for estado in estados_lead:
            status_display = estado['lead_status'] if estado['lead_status'] else 'NULL'
            print(f"   - lead_status '{status_display}': {estado['total']} leads")

        print(f"\n=== RESUMEN ===")
        print(f"Dashboard (básico): {resultado_basico} leads")
        print(f"Calls-Manager (con filtros): {resultado_calls_manager} leads")
        print(f"Diferencia: {resultado_basico - resultado_calls_manager} leads")
        if leads_cerrados > 0:
            print(f"-> La diferencia se debe a {leads_cerrados} leads cerrados que el dashboard cuenta pero calls-manager excluye")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    comparar_consultas()
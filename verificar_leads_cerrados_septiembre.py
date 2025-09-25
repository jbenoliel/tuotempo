#!/usr/bin/env python3
"""
Script para verificar por qué los leads "Volver a llamar"
están cerrados en el archivo de Septiembre
"""

import os
import sys
from db import get_connection

def verificar_leads_cerrados():
    """Analizar por qué los leads 'Volver a llamar' están cerrados"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        print("=== ANÁLISIS LEADS CERRADOS 'VOLVER A LLAMAR' EN SEPTIEMBRE ===")

        # 1. Contar totales
        cursor.execute("""
            SELECT
                COUNT(*) as total_volver_llamar,
                SUM(CASE WHEN lead_status = 'open' OR lead_status IS NULL THEN 1 ELSE 0 END) as abiertos,
                SUM(CASE WHEN lead_status != 'open' AND lead_status IS NOT NULL THEN 1 ELSE 0 END) as cerrados
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%')
        """)
        resumen = cursor.fetchone()
        print(f"\n1. RESUMEN GENERAL:")
        print(f"   Total 'Volver a llamar' en Septiembre: {resumen['total_volver_llamar']}")
        print(f"   - Abiertos: {resumen['abiertos']}")
        print(f"   - Cerrados: {resumen['cerrados']}")

        # 2. Analizar razones de cierre para leads "Volver a llamar" cerrados
        print(f"\n2. ANÁLISIS DE LEADS CERRADOS:")

        # 2a. ¿Tienen cita agendada o manual? (status_level_2)
        cursor.execute("""
            SELECT status_level_2, COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%')
            AND lead_status != 'open' AND lead_status IS NOT NULL
            GROUP BY status_level_2
            ORDER BY total DESC
        """)
        citas = cursor.fetchall()
        print(f"   2a. Por status_level_2 (citas):")
        for cita in citas:
            nivel2 = cita['status_level_2'] if cita['status_level_2'] else 'NULL'
            print(f"       - {nivel2}: {cita['total']} leads")

        # 2b. ¿Han alcanzado el máximo de llamadas?
        cursor.execute("""
            SELECT call_attempts, COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%')
            AND lead_status != 'open' AND lead_status IS NOT NULL
            GROUP BY call_attempts
            ORDER BY call_attempts DESC
        """)
        intentos = cursor.fetchall()
        print(f"   2b. Por número de intentos de llamada:")
        for intento in intentos:
            attempts = intento['call_attempts'] if intento['call_attempts'] else 0
            print(f"       - {attempts} intentos: {intento['total']} leads")

        # 2c. ¿Cuál es el lead_status específico?
        cursor.execute("""
            SELECT lead_status, COUNT(*) as total
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%')
            AND lead_status != 'open' AND lead_status IS NOT NULL
            GROUP BY lead_status
            ORDER BY total DESC
        """)
        estados = cursor.fetchall()
        print(f"   2c. Por lead_status:")
        for estado in estados:
            print(f"       - '{estado['lead_status']}': {estado['total']} leads")

        # 3. Verificar si alguno cambió de estado después (status_level_1)
        cursor.execute("""
            SELECT
                id, nombre, apellidos, telefono, status_level_1, status_level_2,
                lead_status, call_attempts, last_call_time
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%')
            AND lead_status != 'open' AND lead_status IS NOT NULL
            LIMIT 10
        """)
        ejemplos = cursor.fetchall()
        print(f"\n3. EJEMPLOS DE LEADS CERRADOS (primeros 10):")
        for ejemplo in ejemplos:
            nombre = f"{ejemplo['nombre']} {ejemplo['apellidos']}" if ejemplo['nombre'] else "Sin nombre"
            intentos = ejemplo['call_attempts'] or 0
            ultima_llamada = ejemplo['last_call_time'].strftime('%Y-%m-%d %H:%M') if ejemplo['last_call_time'] else 'Nunca'
            status2 = ejemplo['status_level_2'] or 'NULL'
            print(f"   ID {ejemplo['id']}: {nombre}")
            print(f"      Tel: {ejemplo['telefono']}, Status2: {status2}")
            print(f"      Lead_status: {ejemplo['lead_status']}, Intentos: {intentos}, Última: {ultima_llamada}")

        # 4. Verificar límites de intentos (configuración del sistema)
        print(f"\n4. VERIFICAR LÍMITES DEL SISTEMA:")
        cursor.execute("""
            SELECT MAX(call_attempts) as max_intentos, AVG(call_attempts) as promedio_intentos
            FROM leads
            WHERE TRIM(status_level_1) = 'Volver a llamar'
            AND (TRIM(origen_archivo) LIKE '%Septiembre%')
            AND lead_status != 'open' AND lead_status IS NOT NULL
        """)
        limites = cursor.fetchone()
        print(f"   Máximo de intentos en leads cerrados: {limites['max_intentos']}")
        print(f"   Promedio de intentos en leads cerrados: {limites['promedio_intentos']:.1f}")

        cursor.close()
        conn.close()

        print(f"\n=== CONCLUSIONES ===")
        if resumen['cerrados'] > 0:
            print(f"Se encontraron {resumen['cerrados']} leads 'Volver a llamar' cerrados.")
            print("Revisa las razones arriba para determinar si están correctamente cerrados:")
            print("  - ¿Status_level_2 indica cita agendada/manual?")
            print("  - ¿Call_attempts indica máximo de llamadas alcanzado?")
            print("  - ¿Lead_status indica 'No Interesado' u otro estado final?")
        else:
            print("Todos los leads 'Volver a llamar' están abiertos - no hay problema.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_leads_cerrados()
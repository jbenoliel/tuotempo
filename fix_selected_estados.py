#!/usr/bin/env python3
"""
Script para corregir el problema de estado 'selected' incorrecto.
Convertir todos los call_status = 'selected' a 'no_selected'
"""

import os
import sys
import mysql.connector
from config import settings

def get_connection():
    """Obtener conexión a MySQL usando configuración"""
    return mysql.connector.connect(
        host=str(settings.DB_HOST),
        port=int(settings.DB_PORT),
        user=str(settings.DB_USER),
        password=str(settings.DB_PASSWORD),
        database=str(settings.DB_DATABASE),
        ssl_disabled=True,
        autocommit=True,
        charset='utf8mb4',
        use_unicode=True,
        auth_plugin='mysql_native_password'
    )

def fix_selected_estados():
    """Corregir estados 'selected' incorrectos"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        print("=== CORRECCIÓN DE ESTADOS 'SELECTED' INCORRECTOS ===")

        # 1. Contar cuántos leads tienen estado 'selected'
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE call_status = 'selected'
        """)
        total_selected = cursor.fetchone()['total']
        print(f"\n1. Leads con estado 'selected': {total_selected}")

        if total_selected == 0:
            print("   No hay leads con estado 'selected' para corregir.")
            return

        # 2. Mostrar algunos ejemplos
        cursor.execute("""
            SELECT id, nombre, apellidos, telefono, status_level_1, call_status, selected_for_calling
            FROM leads
            WHERE call_status = 'selected'
            LIMIT 5
        """)
        ejemplos = cursor.fetchall()
        print(f"\n2. Ejemplos de leads con estado 'selected':")
        for ejemplo in ejemplos:
            nombre = f"{ejemplo['nombre']} {ejemplo['apellidos']}" if ejemplo['nombre'] else "Sin nombre"
            selected = "SÍ" if ejemplo['selected_for_calling'] else "NO"
            print(f"   ID {ejemplo['id']}: {nombre}")
            print(f"      Tel: {ejemplo['telefono']}, Estado1: {ejemplo['status_level_1']}")
            print(f"      Seleccionado para llamar: {selected}")

        # 3. Corregir todos los estados 'selected' a 'no_selected'
        print(f"\n3. CORRIGIENDO estados 'selected' -> 'no_selected'...")

        cursor.execute("""
            UPDATE leads
            SET call_status = 'no_selected',
                updated_at = NOW()
            WHERE call_status = 'selected'
        """)

        affected_rows = cursor.rowcount
        conn.commit()

        print(f"   ✅ Corregidos {affected_rows} leads")

        # 4. Verificar corrección
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM leads
            WHERE call_status = 'selected'
        """)
        remaining_selected = cursor.fetchone()['total']

        print(f"\n4. VERIFICACIÓN:")
        print(f"   Leads con 'selected' después de corrección: {remaining_selected}")

        if remaining_selected == 0:
            print("   ✅ Corrección completada exitosamente")
        else:
            print("   ⚠️  Aún quedan leads con estado 'selected'")

        # 5. Mostrar distribución de estados después de corrección
        cursor.execute("""
            SELECT call_status, COUNT(*) as total
            FROM leads
            WHERE call_status IS NOT NULL
            GROUP BY call_status
            ORDER BY total DESC
        """)
        distribucion = cursor.fetchall()

        print(f"\n5. DISTRIBUCIÓN FINAL DE ESTADOS:")
        for estado in distribucion:
            print(f"   - {estado['call_status']}: {estado['total']} leads")

        cursor.close()
        conn.close()

        print(f"\n=== CORRECCIÓN COMPLETADA ===")
        print("Ahora todos los leads seleccionados tendrán call_status = 'no_selected'")
        print("El estado 'selected' ya no aparecerá en la interfaz de usuario.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_selected_estados()
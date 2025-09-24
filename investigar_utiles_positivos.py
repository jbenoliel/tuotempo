#!/usr/bin/env python3
"""
Script para investigar la discrepancia en útiles positivos del dashboard
Específicamente para el archivo de septiembre
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import get_connection

def investigar_utiles_positivos():
    """Investiga por qué solo aparecen 4 útiles positivos cuando hay más citas"""

    conn = get_connection()
    if not conn:
        print("ERROR: No se pudo conectar a la base de datos")
        return

    try:
        cursor = conn.cursor(dictionary=True)

        print("🔍 INVESTIGANDO ÚTILES POSITIVOS - ARCHIVO SEPTIEMBRE")
        print("=" * 60)

        # 1. Verificar archivos disponibles
        print("\n1️⃣ ARCHIVOS DISPONIBLES:")
        cursor.execute("SELECT nombre_archivo, total_registros FROM archivos_origen WHERE activo = 1 ORDER BY nombre_archivo")
        archivos = cursor.fetchall()
        for archivo in archivos:
            print(f"   📁 {archivo['nombre_archivo']}: {archivo['total_registros']} registros")

        # 2. Buscar archivo de septiembre
        archivos_septiembre = [a for a in archivos if 'septiembre' in a['nombre_archivo'].lower() or 'sep' in a['nombre_archivo'].lower() or '09' in a['nombre_archivo']]

        if not archivos_septiembre:
            print("\n❓ No se encontró archivo específico de septiembre. Mostrando todos los archivos que podrían ser:")
            for archivo in archivos:
                if any(x in archivo['nombre_archivo'].lower() for x in ['2024', '2025', 'sep']):
                    print(f"   🤔 {archivo['nombre_archivo']}")

            # Usar el primer archivo como ejemplo
            archivo_septiembre = archivos[0]['nombre_archivo'] if archivos else None
            print(f"\n📋 Usando como ejemplo: {archivo_septiembre}")
        else:
            archivo_septiembre = archivos_septiembre[0]['nombre_archivo']
            print(f"\n📋 Archivo de septiembre encontrado: {archivo_septiembre}")

        if not archivo_septiembre:
            print("❌ No hay archivos disponibles")
            return

        # 3. Analizar registros del archivo de septiembre
        print(f"\n2️⃣ ANÁLISIS DETALLADO - {archivo_septiembre}")
        print("-" * 50)

        # Total de registros del archivo
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE origen_archivo = %s", (archivo_septiembre,))
        total_archivo = cursor.fetchone()['total']
        print(f"📊 Total registros en {archivo_septiembre}: {total_archivo}")

        # Citas agendadas (status_level_1 = 'Cita Agendada')
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s AND TRIM(status_level_1) = 'Cita Agendada'
        """, (archivo_septiembre,))
        citas_agendadas = cursor.fetchone()['count']
        print(f"📅 Citas agendadas (status_level_1): {citas_agendadas}")

        # Citas manuales (cita IS NOT NULL)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s AND cita IS NOT NULL
        """, (archivo_septiembre,))
        citas_manuales = cursor.fetchone()['count']
        print(f"✍️ Citas manuales (cita IS NOT NULL): {citas_manuales}")

        # Útiles positivos según nueva lógica
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL)
        """, (archivo_septiembre,))
        utiles_positivos_nuevo = cursor.fetchone()['count']
        print(f"✅ Útiles positivos (nueva lógica): {utiles_positivos_nuevo}")

        # Útiles positivos según lógica anterior
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE origen_archivo = %s
            AND TRIM(status_level_1) = 'Cita Agendada'
        """, (archivo_septiembre,))
        utiles_positivos_anterior = cursor.fetchone()['count']
        print(f"🔄 Útiles positivos (lógica anterior): {utiles_positivos_anterior}")

        print(f"\n📈 DIFERENCIA: +{utiles_positivos_nuevo - utiles_positivos_anterior} útiles positivos con la nueva lógica")

        # 4. Mostrar ejemplos de registros
        print(f"\n3️⃣ EJEMPLOS DE REGISTROS CON CITAS")
        print("-" * 50)

        # Ejemplos de citas agendadas
        print("📅 CITAS AGENDADAS (primeras 5):")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s AND TRIM(status_level_1) = 'Cita Agendada'
            LIMIT 5
        """, (archivo_septiembre,))
        citas_agendadas_ejemplos = cursor.fetchall()

        for i, registro in enumerate(citas_agendadas_ejemplos, 1):
            print(f"   {i}. {registro['nombre']} {registro['apellidos']} ({registro['telefono']})")
            print(f"      Status: {registro['status_level_1']} - {registro['status_level_2']}")
            print(f"      Cita manual: {registro['cita']}")
            print()

        # Ejemplos de citas manuales que NO son agendadas
        print("✍️ CITAS MANUALES SIN STATUS 'Cita Agendada' (primeras 5):")
        cursor.execute("""
            SELECT nombre, apellidos, telefono, status_level_1, status_level_2, cita
            FROM leads
            WHERE origen_archivo = %s
            AND cita IS NOT NULL
            AND (TRIM(status_level_1) != 'Cita Agendada' OR status_level_1 IS NULL)
            LIMIT 5
        """, (archivo_septiembre,))
        citas_manuales_ejemplos = cursor.fetchall()

        for i, registro in enumerate(citas_manuales_ejemplos, 1):
            print(f"   {i}. {registro['nombre']} {registro['apellidos']} ({registro['telefono']})")
            print(f"      Status: {registro['status_level_1']} - {registro['status_level_2']}")
            print(f"      Cita manual: {registro['cita']}")
            print()

        if not citas_manuales_ejemplos:
            print("   ℹ️ No hay citas manuales sin status 'Cita Agendada'")

        # 5. Verificar si hay problema con el dashboard
        print(f"\n4️⃣ VERIFICACIÓN DEL DASHBOARD")
        print("-" * 50)

        # Simular la consulta del dashboard
        cursor.execute("""
            SELECT
                IFNULL(SUM(CASE WHEN (TRIM(status_level_1) = 'Cita Agendada' OR cita IS NOT NULL) THEN 1 ELSE 0 END), 0) AS utiles_positivos,
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Sin Pack' THEN 1 ELSE 0 END), 0) AS cita_sin_pack,
                IFNULL(SUM(CASE WHEN TRIM(status_level_1) = 'Cita Agendada' AND TRIM(status_level_2) = 'Con Pack' THEN 1 ELSE 0 END), 0) AS cita_con_pack
            FROM leads
            WHERE origen_archivo = %s
        """, (archivo_septiembre,))

        dashboard_stats = cursor.fetchone()
        print(f"📊 Dashboard debería mostrar:")
        print(f"   ✅ Útiles positivos: {dashboard_stats['utiles_positivos']}")
        print(f"   📦 Citas con pack: {dashboard_stats['cita_con_pack']}")
        print(f"   📋 Citas sin pack: {dashboard_stats['cita_sin_pack']}")
        print(f"   🧮 Total citas agendadas: {dashboard_stats['cita_con_pack'] + dashboard_stats['cita_sin_pack']}")

        print(f"\n🎯 CONCLUSIÓN:")
        if dashboard_stats['utiles_positivos'] == 4:
            print("❌ El problema persiste. Solo 4 útiles positivos detectados.")
            print("🔍 Posibles causas:")
            print("   1. El cambio no se ha aplicado correctamente")
            print("   2. Hay un problema con el filtro del archivo")
            print("   3. Los datos no están como se esperaba")
        else:
            print(f"✅ El problema se ha corregido. Ahora muestra {dashboard_stats['utiles_positivos']} útiles positivos.")

    except Exception as e:
        print(f"❌ Error durante la investigación: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    investigar_utiles_positivos()
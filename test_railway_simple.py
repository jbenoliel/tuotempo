#!/usr/bin/env python3
"""
Test simple de conexion Railway usando la misma configuracion que el servidor
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Usar exactamente las mismas importaciones que el servidor
try:
    from db import get_connection
    from utils import get_statistics

    print("=== TEST CONEXION RAILWAY ===")

    # Test 1: Conexion directa
    print("\n1. Test conexion directa:")
    conn = get_connection()
    if conn:
        print("   EXITO: Conexion establecida")

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) as total FROM leads LIMIT 1")
            result = cursor.fetchone()
            print(f"   EXITO: Hay {result['total']} leads en total")

            # Test rapido de archivos
            cursor.execute("SELECT nombre_archivo FROM archivos_origen WHERE activo = 1 LIMIT 5")
            archivos = cursor.fetchall()
            print(f"   EXITO: {len(archivos)} archivos disponibles:")
            for archivo in archivos:
                print(f"      - {archivo['nombre_archivo']}")

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"   ERROR en consulta: {e}")
    else:
        print("   ERROR: No se pudo establecer conexion")

    # Test 2: Funcion get_statistics
    print("\n2. Test funcion get_statistics:")
    try:
        stats = get_statistics()
        print(f"   Total leads: {stats.get('total_leads', 'N/A')}")
        print(f"   Utiles positivos: {stats.get('estados', {}).get('utiles_positivos', 'N/A')}")
        print(f"   Archivos disponibles: {len(stats.get('archivos_disponibles', []))}")

        # Mostrar archivos
        for archivo in stats.get('archivos_disponibles', [])[:3]:
            print(f"      - {archivo.get('nombre_archivo')}: {archivo.get('total_registros')} registros")

        if stats.get('total_leads', 0) > 0:
            print("   EXITO: get_statistics funciona correctamente")
        else:
            print("   WARNING: get_statistics devuelve 0 leads")

    except Exception as e:
        print(f"   ERROR en get_statistics: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"ERROR importando modulos: {e}")
except Exception as e:
    print(f"ERROR general: {e}")
    import traceback
    traceback.print_exc()
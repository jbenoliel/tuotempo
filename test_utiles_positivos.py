#!/usr/bin/env python3
"""
Test directo de la funcion get_statistics modificada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar la funcion modificada
from utils import get_statistics

def test_utiles_positivos():
    """Prueba la funcion get_statistics directamente"""

    print("TESTING FUNCION get_statistics MODIFICADA")
    print("=" * 50)

    try:
        # Obtener estadisticas sin filtro
        print("\n1. ESTADISTICAS SIN FILTRO:")
        stats_sin_filtro = get_statistics()
        print(f"Total leads: {stats_sin_filtro['total_leads']}")
        print(f"Utiles positivos: {stats_sin_filtro['estados']['utiles_positivos']}")
        print(f"Citas con pack: {stats_sin_filtro['estados']['cita_con_pack']}")
        print(f"Citas sin pack: {stats_sin_filtro['estados']['cita_sin_pack']}")
        print(f"Contactados: {stats_sin_filtro['contactados']}")

        # Mostrar archivos disponibles
        print(f"\n2. ARCHIVOS DISPONIBLES:")
        for archivo in stats_sin_filtro['archivos_disponibles']:
            print(f"   {archivo['nombre_archivo']}: {archivo['total_registros']} registros")

        # Probar con filtro de archivo de septiembre si existe
        archivos_septiembre = [a for a in stats_sin_filtro['archivos_disponibles']
                              if 'septiembre' in a['nombre_archivo'].lower() or
                                 'sep' in a['nombre_archivo'].lower() or
                                 '09' in a['nombre_archivo']]

        if archivos_septiembre:
            archivo_septiembre = archivos_septiembre[0]['nombre_archivo']
            print(f"\n3. ESTADISTICAS CON FILTRO - {archivo_septiembre}:")
            stats_filtrado = get_statistics(filtro_origen_archivo=archivo_septiembre)

            print(f"Total leads (filtrado): {stats_filtrado['total_leads']}")
            print(f"Utiles positivos (filtrado): {stats_filtrado['estados']['utiles_positivos']}")
            print(f"Citas con pack (filtrado): {stats_filtrado['estados']['cita_con_pack']}")
            print(f"Citas sin pack (filtrado): {stats_filtrado['estados']['cita_sin_pack']}")
            print(f"Contactados (filtrado): {stats_filtrado['contactados']}")

            print(f"\nCOMPARACION:")
            print(f"Sin filtro - Utiles positivos: {stats_sin_filtro['estados']['utiles_positivos']}")
            print(f"Con filtro - Utiles positivos: {stats_filtrado['estados']['utiles_positivos']}")

            if stats_filtrado['estados']['utiles_positivos'] == 4:
                print("\nPROBLEMA: Sigue mostrando solo 4 utiles positivos")
                print("Posible causa: El problema no esta en la funcion sino en otra parte")
            else:
                print(f"\nSOLUCIONADO: Ahora muestra {stats_filtrado['estados']['utiles_positivos']} utiles positivos")
        else:
            print(f"\n3. No se encontro archivo de septiembre especifico")
            # Usar el primer archivo disponible como prueba
            if stats_sin_filtro['archivos_disponibles']:
                primer_archivo = stats_sin_filtro['archivos_disponibles'][0]['nombre_archivo']
                print(f"Probando con primer archivo: {primer_archivo}")
                stats_primer = get_statistics(filtro_origen_archivo=primer_archivo)
                print(f"Utiles positivos: {stats_primer['estados']['utiles_positivos']}")

    except Exception as e:
        print(f"Error durante el test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_utiles_positivos()
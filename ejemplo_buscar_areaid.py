#!/usr/bin/env python3
"""
Ejemplo simple de uso del buscador de areaId para Excel

Este script muestra cómo usar el programa buscar_areaid_excel.py
con configuraciones típicas.
"""

import os
import subprocess
import sys

def run_areaid_search():
    """Ejecuta la búsqueda de areaId con configuración típica"""
    
    # Configuración típica para archivos de Segurcaixa
    excel_path = input("📁 Ruta del archivo Excel: ").strip()
    
    if not excel_path:
        print("❌ Debes especificar la ruta del archivo Excel")
        return
    
    if not os.path.exists(excel_path):
        print(f"❌ No se encontró el archivo: {excel_path}")
        return
    
    # Preguntar por las columnas
    print("\n🔍 ¿Qué columnas quieres usar para la búsqueda?")
    print("Ejemplos comunes:")
    print("  - NOMBRE_CLINICA")
    print("  - DIRECCION_CLINICA") 
    print("  - Nombre")
    print("  - Dirección")
    print("  - Centro")
    print("  - Clínica")
    
    nombre_col = input("\n👤 Nombre de la columna con el nombre de la clínica (Enter para omitir): ").strip()
    direccion_col = input("📍 Nombre de la columna con la dirección (Enter para omitir): ").strip()
    
    if not nombre_col and not direccion_col:
        print("❌ Debes especificar al menos una columna (nombre o dirección)")
        return
    
    # Construir el comando
    cmd = [sys.executable, "buscar_areaid_excel.py", "--excel", excel_path]
    
    if nombre_col:
        cmd.extend(["--nombre", nombre_col])
    
    if direccion_col:
        cmd.extend(["--direccion", direccion_col])
    
    print(f"\n🚀 Ejecutando: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Ejecutar el comando
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n🎉 ¡Proceso completado!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al ejecutar el proceso: {e}")
    except FileNotFoundError:
        print("\n❌ No se encontró el archivo buscar_areaid_excel.py")
        print("Asegúrate de estar en el directorio correcto del proyecto")

def main():
    print("🏥 Buscador de areaId para Excel - Ejemplo de Uso")
    print("=" * 50)
    print()
    print("Este programa te ayuda a encontrar los areaId de clínicas")
    print("basándose en el nombre y/o dirección desde un archivo Excel.")
    print()
    
    # Verificar que existe el script principal
    if not os.path.exists("buscar_areaid_excel.py"):
        print("❌ Error: No se encontró buscar_areaid_excel.py en el directorio actual")
        print("Asegúrate de estar en el directorio del proyecto TuoTempo")
        return
    
    try:
        run_areaid_search()
    except KeyboardInterrupt:
        print("\n\n👋 Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()

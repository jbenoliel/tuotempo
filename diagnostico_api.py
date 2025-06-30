#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnóstico para verificar la configuración de la API.
"""

import sys
import os
import importlib.util

def check_module(module_name):
    """Verifica si un módulo está instalado y muestra su versión"""
    try:
        module = __import__(module_name)
        print(f"✅ {module_name} está instalado (versión: {getattr(module, '__version__', 'desconocida')})")
        return True
    except ImportError:
        print(f"❌ {module_name} NO está instalado")
        return False

def check_file_exists(file_path):
    """Verifica si un archivo existe"""
    if os.path.isfile(file_path):
        print(f"✅ El archivo {file_path} existe")
        return True
    else:
        print(f"❌ El archivo {file_path} NO existe")
        return False

def check_api_endpoints():
    """Verifica los endpoints de la API"""
    try:
        from api_resultado_llamada import app as api_app
        
        print("\n=== ENDPOINTS DE LA API ===")
        for rule in api_app.url_map.iter_rules():
            print(f"Ruta: {rule.rule}")
            print(f"  Endpoint: {rule.endpoint}")
            print(f"  Métodos: {', '.join(rule.methods)}")
            print()
        return True
    except Exception as e:
        print(f"❌ Error al verificar endpoints de API: {str(e)}")
        return False

def main():
    """Función principal"""
    print("=== DIAGNÓSTICO DE CONFIGURACIÓN DE API ===")
    print(f"Python: {sys.version}")
    print(f"Ejecutando desde: {sys.executable}")
    print(f"Directorio actual: {os.getcwd()}")
    
    print("\n=== VERIFICACIÓN DE MÓDULOS ===")
    modules = ['flask', 'mysql.connector', 'pandas', 'requests']
    all_modules_ok = all(check_module(module) for module in modules)
    
    print("\n=== VERIFICACIÓN DE ARCHIVOS ===")
    files = [
        'app.py',
        'app_dashboard.py',
        'api_resultado_llamada.py',
        'config.py'
    ]
    all_files_ok = all(check_file_exists(file) for file in files)
    
    # Verificar endpoints de API
    api_ok = check_api_endpoints()
    
    print("\n=== RESUMEN ===")
    if all_modules_ok:
        print("✅ Todos los módulos necesarios están instalados")
    else:
        print("❌ Faltan algunos módulos necesarios")
    
    if all_files_ok:
        print("✅ Todos los archivos necesarios existen")
    else:
        print("❌ Faltan algunos archivos necesarios")
    
    if api_ok:
        print("✅ La API está configurada correctamente")
    else:
        print("❌ Hay problemas con la configuración de la API")
    
    print("\nPara ejecutar la aplicación correctamente, asegúrate de estar en el entorno virtual:")
    print("1. Activa el entorno virtual: venv\\Scripts\\activate (Windows) o source venv/bin/activate (Linux/Mac)")
    print("2. Ejecuta la aplicación: python app_dashboard.py")
    print("3. En otra terminal (también con el entorno virtual activado), ejecuta: python test_api_simple.py")

if __name__ == "__main__":
    main()

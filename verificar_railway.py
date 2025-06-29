#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar que la API en Railway funciona correctamente.
"""

import requests
import json
import sys

# URL base de la API en Railway (reemplaza con tu URL real)
API_BASE_URL = "https://tuotempo-production.up.railway.app"  # Ajusta según tu URL real

def verificar_ruta_basica():
    """Verifica que la aplicación base esté respondiendo"""
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"\n=== VERIFICACIÓN DE RUTA BASE ===\n")
        print(f"Status code: {response.status_code}")
        print(f"Contenido: {response.text[:100]}..." if len(response.text) > 100 else f"Contenido: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"\n=== ERROR EN RUTA BASE ===\n")
        print(f"Error: {str(e)}")
        return False

def verificar_api_status():
    """Verifica que la API esté respondiendo correctamente"""
    try:
        print(f"\n=== INTENTANDO ACCEDER A /api/status ===\n")
        print(f"URL completa: {API_BASE_URL}/api/status")
        response = requests.get(f"{API_BASE_URL}/api/status")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[OK] API Status: OK")
            print(f"   Mensaje: {data.get('message', 'No message')}")
            return True
        else:
            print(f"[ERROR] Error en API Status: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error al conectar con la API: {str(e)}")
        return False

def verificar_recargar_excel():
    """Verifica que el endpoint /recargar-excel esté funcionando"""
    try:
        print(f"\n=== VERIFICANDO ENDPOINT /recargar-excel ===\n")
        print(f"URL completa: {API_BASE_URL}/recargar-excel")
        response = requests.get(f"{API_BASE_URL}/recargar-excel")
        print(f"Status code: {response.status_code}")
        print(f"Contenido: {response.text[:100]}..." if len(response.text) > 100 else f"Contenido: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Error al conectar con /recargar-excel: {str(e)}")
        return False

def verificar_telefono_especifico(telefono):
    """Verifica que un teléfono específico exista en la base de datos"""
    try:
        print(f"\n=== VERIFICANDO TELÉFONO {telefono} ===\n")
        print(f"URL completa: {API_BASE_URL}/api/actualizar_resultado?telefono={telefono}&cita=false&conPack=false&no_interesado=false")
        
        # Usamos el endpoint de actualizar_resultado solo para verificar
        # Pasamos parámetros que no modifican nada
        response = requests.get(
            f"{API_BASE_URL}/api/actualizar_resultado",
            params={
                "telefono": telefono,
                "cita": False,
                "conPack": False,
                "no_interesado": False
            }
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Contenido: {response.text[:100]}..." if len(response.text) > 100 else f"Contenido: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success', False):
                    print(f"[OK] Teléfono {telefono} encontrado en la base de datos")
                    return True
                else:
                    print(f"[ERROR] Teléfono {telefono} no encontrado: {data.get('message', 'No message')}")
                    return False
            except json.JSONDecodeError:
                print(f"[ERROR] La respuesta no es JSON válido: {response.text}")
                return False
        else:
            print(f"[ERROR] Error al verificar teléfono: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error al conectar con la API: {str(e)}")
        return False

def main():
    print("\n===== VERIFICACIÓN DE API EN RAILWAY =====\n")
    print(f"URL base: {API_BASE_URL}")
    
    # Verificar ruta base
    verificar_ruta_basica()
    
    # Verificar endpoint /recargar-excel
    verificar_recargar_excel()
    
    # Verificar API status
    verificar_api_status()
    
    # Verificar teléfonos
    telefonos_prueba = [
        "672663119",  # ADAM PEREIRA DUARTE
        "614421251",  # VIOLETA RAMONA CONSTANTIN
        "627614713"   # LETICIA COLAS TEJERO
    ]
    
    print("\n=== VERIFICACIÓN DE TELÉFONOS ===\n")
    for telefono in telefonos_prueba:
        verificar_telefono_especifico(telefono)
    
    print("\n===== FIN DE LA VERIFICACIÓN =====\n")
    print("Si todo está en verde ([OK]), la API está funcionando correctamente en Railway.")
    print("Si hay errores ([ERROR]), revisa los logs de Railway y asegúrate de que:")
    print("1. La base de datos está correctamente configurada")
    print("2. El despliegue se completó sin errores")
    print("3. La URL de la API es correcta")

if __name__ == "__main__":
    main()

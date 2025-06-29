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

def verificar_api_status():
    """Verifica que la API esté respondiendo correctamente"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ API Status: OK")
            print(f"   Mensaje: {data.get('message', 'No message')}")
            return True
        else:
            print(f"❌ Error en API Status: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error al conectar con la API: {str(e)}")
        return False

def verificar_telefono_especifico(telefono):
    """Verifica que un teléfono específico exista en la base de datos"""
    try:
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
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success', False):
                print(f"✅ Teléfono {telefono} encontrado en la base de datos")
                return True
            else:
                print(f"❌ Teléfono {telefono} no encontrado: {data.get('message', 'No message')}")
                return False
        else:
            print(f"❌ Error al verificar teléfono: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error al conectar con la API: {str(e)}")
        return False

def main():
    print("\n=== VERIFICACIÓN DE API EN RAILWAY ===\n")
    
    # Verificar que la API responde
    if not verificar_api_status():
        print("\n❌ La API no está respondiendo correctamente. Verifica la URL y el despliegue.")
        sys.exit(1)
    
    # Verificar algunos teléfonos específicos
    telefonos_prueba = [
        "672663119",  # ADAM PEREIRA DUARTE
        "614421251",  # VIOLETA RAMONA CONSTANTIN
        "627614713"   # LETICIA COLAS TEJERO
    ]
    
    print("\n=== VERIFICACIÓN DE TELÉFONOS ===\n")
    for telefono in telefonos_prueba:
        verificar_telefono_especifico(telefono)
    
    print("\n=== VERIFICACIÓN COMPLETA ===\n")
    print("Si todo está en verde (✅), la API está funcionando correctamente en Railway.")
    print("Si hay errores (❌), revisa los logs de Railway y asegúrate de que:")
    print("1. La base de datos está correctamente configurada")
    print("2. El despliegue se completó sin errores")
    print("3. La URL de la API es correcta")

if __name__ == "__main__":
    main()

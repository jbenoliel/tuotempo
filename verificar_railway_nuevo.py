#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para verificar que la aplicación está correctamente desplegada en Railway.
Verifica todos los endpoints principales, incluyendo la API de resultados de llamadas.
"""

import requests
import sys
import json
import time
from datetime import datetime

# URL base de la aplicación en Railway
BASE_URL = "https://tuotempo-production.up.railway.app"

def verificar_endpoint(url, metodo="GET", datos=None, descripcion="", mostrar_respuesta=False):
    """Verifica que un endpoint esté funcionando correctamente"""
    print(f"Verificando {descripcion} ({url})...")
    try:
        if metodo == "GET":
            response = requests.get(url, timeout=15)
        elif metodo == "POST":
            response = requests.post(url, json=datos, timeout=15)
        else:
            print(f"[ERROR] Método no soportado: {metodo}")
            return False, None
        
        if response.status_code == 200:
            print(f"[OK] {descripcion} - Código: {response.status_code}")
            if mostrar_respuesta:
                try:
                    json_resp = response.json()
                    print(f"Respuesta: {json.dumps(json_resp, indent=2, ensure_ascii=False)[:500]}...")
                except:
                    print(f"Respuesta (no JSON): {response.text[:200]}...")
            return True, response
        else:
            print(f"[ERROR] {descripcion} - Código: {response.status_code}, Respuesta: {response.text[:100]}")
            return False, response
    except Exception as e:
        print(f"[ERROR] {descripcion} - Excepción: {str(e)}")
        return False, None

def verificar_api_completa():
    """Verifica todos los endpoints de la API de resultados de llamadas"""
    print("\n=== VERIFICACIÓN DE LA API DE RESULTADOS DE LLAMADAS ===")
    
    # 1. Verificar status de la API
    api_ok, _ = verificar_endpoint(f"{BASE_URL}/api/status", descripcion="API Status", mostrar_respuesta=True)
    if not api_ok:
        print("La API no está disponible. Saltando pruebas adicionales.")
        return False
    
    # 2. Obtener resultados y extraer un teléfono para pruebas
    resultados_ok, response = verificar_endpoint(
        f"{BASE_URL}/api/obtener_resultados",
        descripcion="API Obtener Resultados"
    )
    
    if not resultados_ok or not response:
        print("No se pudieron obtener resultados. Saltando pruebas adicionales.")
        return False
    
    # Intentar extraer un teléfono para pruebas
    try:
        data = response.json()
        if data.get("count", 0) > 0 and len(data.get("contactos", [])) > 0:
            telefono_prueba = data["contactos"][0]["telefono"]
            print(f"Usando teléfono de prueba: {telefono_prueba}")
        else:
            print("No hay contactos disponibles para pruebas.")
            return False
    except Exception as e:
        print(f"Error al procesar resultados: {str(e)}")
        return False
    
    # 3. Actualizar resultado de llamada
    datos_prueba = {
        "telefono": telefono_prueba,
        "no_interesado": True
    }
    
    actualizar_ok, _ = verificar_endpoint(
        f"{BASE_URL}/api/actualizar_resultado",
        metodo="POST",
        datos=datos_prueba,
        descripcion="API Actualizar Resultado",
        mostrar_respuesta=True
    )
    
    # 4. Verificar que el resultado se haya actualizado
    if actualizar_ok:
        time.sleep(2)  # Pequeña pausa para asegurar que la actualización se complete
        verificar_ok, response = verificar_endpoint(
            f"{BASE_URL}/api/obtener_resultados",
            descripcion="Verificar Actualización"
        )
        
        if verificar_ok and response:
            try:
                data = response.json()
                for contacto in data.get("contactos", []):
                    if contacto.get("telefono") == telefono_prueba:
                        if contacto.get("resultado_llamada") == "no interesado":
                            print(f"[OK] Resultado actualizado correctamente para {telefono_prueba}")
                            return True
                        else:
                            print(f"[ERROR] El resultado no se actualizó correctamente. Valor actual: {contacto.get('resultado_llamada')}")
                            return False
                print(f"[ERROR] No se encontró el teléfono {telefono_prueba} en los resultados")
                return False
            except Exception as e:
                print(f"Error al verificar actualización: {str(e)}")
                return False
    
    return actualizar_ok

def verificar_admin_login():
    """Verifica que la página de login esté disponible"""
    print("\n=== VERIFICACIÓN DEL SISTEMA DE ADMINISTRACIÓN ===")
    login_ok, _ = verificar_endpoint(f"{BASE_URL}/login", descripcion="Página de Login")
    return login_ok

def main():
    """Función principal"""
    print("=== VERIFICACIÓN DE DESPLIEGUE EN RAILWAY ===")
    print(f"URL base: {BASE_URL}")
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar que la aplicación esté en línea
    app_ok, _ = verificar_endpoint(f"{BASE_URL}/", descripcion="Página principal")
    if not app_ok:
        print("\nLa aplicación no está en línea. Verifica el despliegue en Railway.")
        return False
    
    # Verificar endpoint de recarga de Excel
    recarga_ok, _ = verificar_endpoint(f"{BASE_URL}/recargar-excel", descripcion="Endpoint de recarga de Excel")
    
    # Verificar API completa
    api_ok = verificar_api_completa()
    
    # Verificar sistema de administración
    admin_ok = verificar_admin_login()
    
    print("\n=== RESUMEN DE VERIFICACIÓN ===")
    print(f"Aplicación principal: {'✅ OK' if app_ok else '❌ ERROR'}")
    print(f"Recarga de Excel: {'✅ OK' if recarga_ok else '❌ ERROR'}")
    print(f"API de resultados: {'✅ OK' if api_ok else '❌ ERROR'}")
    print(f"Sistema de administración: {'✅ OK' if admin_ok else '❌ ERROR'}")
    
    if app_ok and recarga_ok and api_ok and admin_ok:
        print("\n✅ TODO CORRECTO: La aplicación está funcionando correctamente en Railway.")
    else:
        print("\n❌ HAY PROBLEMAS: Algunos componentes de la aplicación no están funcionando correctamente.")
        print("Revisa los logs de Railway y asegúrate de que:")
        print("1. La base de datos está correctamente configurada")
        print("2. El despliegue se completó sin errores")
        print("3. Las variables de entorno están configuradas correctamente")
        print("4. El punto de entrada de la aplicación es 'app:app'")
    
    return app_ok and recarga_ok and api_ok and admin_ok

if __name__ == "__main__":
    main()

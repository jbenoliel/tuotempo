#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ejemplo de uso de la API de resultados de llamadas de TuoTempo

Este script muestra cómo utilizar los diferentes endpoints de la API
para verificar su estado, obtener contactos y actualizar resultados de llamadas.
"""

import requests
import json
from datetime import datetime
import time
import sys

# URL base de la API - Ajusta según tu configuración
API_BASE_URL = "http://localhost:5000/api"  # Puerto por defecto 5000

def verificar_estado():
    """Verifica si la API está en línea"""
    try:
        response = requests.get(f"{API_BASE_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"API en línea: {data['timestamp']}")
            return True
        else:
            print(f"Error al verificar estado: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def actualizar_resultado_llamada(telefono, fecha_cita=None, hora_cita=None, con_pack=False, no_interesado=False):
    """
    Actualiza el resultado de una llamada según los parámetros
    
    Args:
        telefono (str): Número de teléfono del contacto
        fecha_cita (str, optional): Fecha de la cita (formato DD/MM/YYYY)
        hora_cita (str, optional): Hora de la cita (formato HH:MM o HH:MM:SS)
        con_pack (bool, optional): Si la cita incluye pack
        no_interesado (bool, optional): Si el contacto no está interesado
        
    Returns:
        dict: Respuesta de la API
    """
    url = f"{API_BASE_URL}/actualizar_resultado"
    
    # Preparar datos
    data = {
        "telefono": telefono,
        "noInteresado": no_interesado
    }
    
    if fecha_cita:
        data["nuevaCita"] = fecha_cita
        data["conPack"] = con_pack
        
    if hora_cita:
        data["horaCita"] = hora_cita
    
    # Hacer la solicitud
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if response.status_code == 200:
            print(f"✅ Resultado actualizado: {result['resultado']} para {telefono}")
        else:
            print(f"❌ Error: {result.get('error', 'Desconocido')}")
        
        return result
    except Exception as e:
        print(f"Error de conexión: {e}")
        return {"error": str(e)}

def obtener_contactos(filtro_resultado=None):
    """
    Obtiene la lista de contactos con un filtro opcional de resultado
    
    Args:
        filtro_resultado (str, optional): Filtro por resultado de llamada
        
    Returns:
        list: Lista de contactos
    """
    url = f"{API_BASE_URL}/obtener_resultados"
    params = {}
    
    if filtro_resultado:
        params["resultado"] = filtro_resultado
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"Se encontraron {data['count']} contactos")
            
            # Mostrar resumen de contactos
            for contacto in data.get("contactos", []):
                print(f"- {contacto.get('nombre', '')} {contacto.get('apellidos', '')}")
                print(f"  Tel: {contacto.get('telefono', '')}")
                print(f"  Resultado: {contacto.get('resultado_llamada', 'No definido')}")
                if contacto.get('cita'):
                    pack_str = "Con pack" if contacto.get('conPack') else "Sin pack"
                    print(f"  Cita: {contacto['cita']} ({pack_str})")
                print()
                
            return data.get("contactos", [])
        else:
            print(f"Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error de conexión: {e}")
        return []

def main():
    """Función principal para demostrar el uso de la API"""
    print("=== EJEMPLO DE USO DE LA API DE RESULTADOS DE LLAMADAS ===")
    print(f"URL base: {API_BASE_URL}")
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nEste script muestra cómo utilizar los diferentes endpoints de la API.")
    print("Sigue las instrucciones para probar cada funcionalidad.")
    
    # Verificar estado de la API
    print("\n=== 1. VERIFICANDO ESTADO DE LA API ===")
    if not verificar_estado():
        print("\n❌ La API no está disponible. Asegúrate de que el servidor esté en ejecución.")
        print("Comando para iniciar el servidor: python app_dashboard.py")
        return
    
    # Obtener todos los contactos
    print("\n=== 2. OBTENIENDO TODOS LOS CONTACTOS ===")
    contactos = obtener_contactos()
    if not contactos:
        print("\n❌ No se pudieron obtener contactos. Verifica la conexión a la base de datos.")
        return
    
    total_contactos = len(contactos)
    print(f"\n✅ Se encontraron {total_contactos} contactos en la base de datos")
    
    # Mostrar algunos contactos de ejemplo
    if total_contactos > 0:
        print("\nEjemplos de contactos:")
        for i, contacto in enumerate(contactos[:3]):  # Mostrar solo los primeros 3
            print(f"  {i+1}. {contacto.get('nombre', '')} {contacto.get('apellidos', '')} - Tel: {contacto.get('telefono', '')}")
    
    # Filtrar contactos por resultado
    print("\n=== 3. FILTRANDO CONTACTOS POR RESULTADO ===")
    print("Buscando contactos marcados como 'no interesado'...")
    contactos_filtrados = obtener_contactos(filtro_resultado="no interesado")
    print(f"\n✅ Se encontraron {len(contactos_filtrados)} contactos marcados como 'no interesado'")
    
    # Seleccionar un contacto para actualizar
    if total_contactos > 0:
        # Tomamos el primer contacto como ejemplo
        contacto = contactos[0]  
        telefono = contacto.get('telefono')
        nombre_completo = f"{contacto.get('nombre', '')} {contacto.get('apellidos', '')}"
        
        print(f"\n=== 4. ACTUALIZANDO RESULTADO PARA {nombre_completo} ({telefono}) ===")
        
        # Ejemplo 1: Marcar como no interesado
        print("\n4.1. Marcando como NO INTERESADO...")
        resultado = actualizar_resultado_llamada(telefono, no_interesado=True)
        if resultado.get('success', False):
            print(f"\n✅ Resultado actualizado correctamente: {resultado.get('message', '')}")
        else:
            print(f"\n❌ Error al actualizar: {resultado.get('error', 'Error desconocido')}")
        
        # Esperar un momento para que la base de datos se actualice
        print("\nEsperando 2 segundos para que la base de datos se actualice...")
        time.sleep(2)
        
        # Verificar los cambios
        print("\n=== 5. VERIFICANDO CAMBIOS ===")
        contactos_actualizados = obtener_contactos()
        encontrado = False
        for c in contactos_actualizados:
            if c.get('telefono') == telefono:
                encontrado = True
                print(f"\nEstado actual del contacto {nombre_completo} ({telefono}):")
                print(f"  - Resultado llamada: {c.get('resultado_llamada')}")
                print(f"  - Cita: {c.get('cita')}")
                print(f"  - Con pack: {c.get('conPack')}")
                break
        
        if not encontrado:
            print(f"\n❌ No se encontró el contacto con teléfono {telefono}")
        
        # Ejemplo 2: Programar una cita
        print("\n=== 6. PROGRAMANDO UNA CITA ===")
        # Formato de fecha DD/MM/YYYY
        fecha_cita = datetime.now().strftime("%d/%m/%Y")
        # Formato de hora HH:MM:SS
        hora_cita = datetime.now().strftime("%H:%M:%S")
        print(f"Programando cita para {nombre_completo} el {fecha_cita} a las {hora_cita}...")
        resultado = actualizar_resultado_llamada(telefono, fecha_cita=fecha_cita, hora_cita=hora_cita, con_pack=True)
        if resultado.get('success', False):
            print(f"\n✅ Cita programada correctamente: {resultado.get('message', '')}")
        else:
            print(f"\n❌ Error al programar cita: {resultado.get('error', 'Error desconocido')}")
    else:
        print("\n❌ No hay contactos disponibles para actualizar")
    
    print("\n=== RESUMEN DE LA PRUEBA ===")
    print("\n✅ Se ha completado la prueba de la API de resultados de llamadas")
    print("Para más información, consulta la documentación en API_DOCUMENTATION.md")
    print("\n=== FIN DEL EJEMPLO ===")

if __name__ == "__main__":
    main()

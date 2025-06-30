#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para verificar el funcionamiento completo de la API de resultados de llamadas.
Prueba todos los endpoints y verifica que funcionen correctamente con datos reales.
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
import random
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URL base para pruebas (cambiar según el entorno)
# BASE_URL = "http://localhost:5000"  # Local
BASE_URL = "https://tuotempo-production.up.railway.app"  # Railway

def verificar_api_status():
    """Verifica que el endpoint /api/status esté funcionando"""
    url = f"{BASE_URL}/api/status"
    logger.info(f"Verificando API status en: {url}")
    
    try:
        # Usar verify=False para evitar problemas de certificados en entornos de desarrollo
        response = requests.get(url, timeout=10, verify=False)
        logger.info(f"Código de respuesta: {response.status_code}")
        logger.info(f"Contenido de respuesta: {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"✅ API status OK: {data}")
                return True
            except json.JSONDecodeError as je:
                logger.error(f"❌ Error al decodificar JSON: {je}. Respuesta: {response.text[:200]}")
                return False
        else:
            logger.error(f"❌ Error en API status. Código: {response.status_code}, Respuesta: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError as ce:
        logger.error(f"❌ Error de conexión: {str(ce)}")
        logger.info("Comprueba que el servidor Flask esté ejecutándose en la URL especificada")
        return False
    except Exception as e:
        logger.error(f"❌ Error al conectar con API status: {str(e)}")
        return False

def obtener_telefonos_disponibles():
    """Obtiene una lista de teléfonos disponibles en la base de datos"""
    url = f"{BASE_URL}/api/obtener_resultados"
    logger.info(f"Obteniendo teléfonos disponibles desde: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("count") > 0:
                telefonos = [contacto["telefono"] for contacto in data["contactos"] if contacto.get("telefono")]
                logger.info(f"✅ Se encontraron {len(telefonos)} teléfonos disponibles")
                return telefonos
            else:
                logger.warning("⚠️ No se encontraron contactos en la base de datos")
                return []
        else:
            logger.error(f"❌ Error al obtener teléfonos. Código: {response.status_code}, Respuesta: {response.text}")
            return []
    except Exception as e:
        logger.error(f"❌ Error al conectar para obtener teléfonos: {str(e)}")
        return []

def actualizar_resultado_llamada(telefono, escenario):
    """
    Actualiza el resultado de una llamada según diferentes escenarios
    
    Escenarios:
    1 - Llamada cortada (volver a marcar)
    2 - No interesado
    3 - Cita sin pack
    4 - Cita con pack
    """
    url = f"{BASE_URL}/api/actualizar_resultado"
    
    # Datos base
    data = {
        "telefono": telefono,
        "cita": None,
        "conPack": False,
        "no_interesado": False
    }
    
    # Configurar según escenario
    if escenario == 1:
        # Llamada cortada - volver a marcar (valores por defecto)
        escenario_desc = "Llamada cortada (volver a marcar)"
    elif escenario == 2:
        # No interesado
        data["no_interesado"] = True
        escenario_desc = "No interesado"
    elif escenario == 3:
        # Cita sin pack
        fecha_cita = (datetime.now() + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d %H:%M:%S")
        data["cita"] = fecha_cita
        data["conPack"] = False
        escenario_desc = f"Cita sin pack para {fecha_cita}"
    elif escenario == 4:
        # Cita con pack
        fecha_cita = (datetime.now() + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d %H:%M:%S")
        data["cita"] = fecha_cita
        data["conPack"] = True
        escenario_desc = f"Cita con pack para {fecha_cita}"
    else:
        logger.error(f"❌ Escenario no válido: {escenario}")
        return False
    
    logger.info(f"Actualizando teléfono {telefono} con escenario {escenario}: {escenario_desc}")
    logger.info(f"Datos a enviar: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                logger.info(f"✅ Actualización exitosa: {result}")
                return True
            else:
                logger.error(f"❌ Error en la actualización: {result}")
                return False
        else:
            logger.error(f"❌ Error al actualizar. Código: {response.status_code}, Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error al conectar para actualizar: {str(e)}")
        return False

def verificar_resultado_actualizado(telefono, resultado_esperado):
    """Verifica que el resultado de la llamada se haya actualizado correctamente"""
    url = f"{BASE_URL}/api/obtener_resultados"
    logger.info(f"Verificando resultado para teléfono {telefono}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("count") > 0:
                # Buscar el teléfono en los resultados
                for contacto in data["contactos"]:
                    if contacto.get("telefono") == telefono:
                        resultado_actual = contacto.get("resultado_llamada")
                        if resultado_actual == resultado_esperado:
                            logger.info(f"✅ Verificación exitosa: Resultado '{resultado_actual}' coincide con lo esperado")
                            return True
                        else:
                            logger.error(f"❌ Verificación fallida: Resultado '{resultado_actual}' no coincide con '{resultado_esperado}'")
                            return False
                
                logger.error(f"❌ No se encontró el teléfono {telefono} en los resultados")
                return False
            else:
                logger.error("❌ No se encontraron contactos en la respuesta")
                return False
        else:
            logger.error(f"❌ Error al verificar. Código: {response.status_code}, Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error al conectar para verificar: {str(e)}")
        return False

def ejecutar_prueba_completa():
    """Ejecuta una prueba completa de la API"""
    logger.info("=== INICIANDO PRUEBA COMPLETA DE LA API ===")
    
    # Paso 1: Verificar que la API esté en línea
    if not verificar_api_status():
        logger.error("❌ La API no está disponible. Abortando pruebas.")
        return False
    
    # Paso 2: Obtener teléfonos disponibles
    telefonos = obtener_telefonos_disponibles()
    if not telefonos:
        logger.error("❌ No hay teléfonos disponibles para probar. Abortando pruebas.")
        return False
    
    # Seleccionar algunos teléfonos para pruebas (máximo 4)
    telefonos_prueba = telefonos[:min(4, len(telefonos))]
    
    # Mapeo de escenarios a resultados esperados
    escenarios = {
        1: "volver a marcar",
        2: "no interesado",
        3: "cita sin pack",
        4: "cita con pack"
    }
    
    # Paso 3: Probar cada escenario con un teléfono diferente
    resultados_pruebas = []
    
    for i, telefono in enumerate(telefonos_prueba):
        escenario = (i % 4) + 1  # Escenarios del 1 al 4
        resultado_esperado = escenarios[escenario]
        
        logger.info(f"\n=== PRUEBA {i+1}: Teléfono {telefono}, Escenario {escenario} ({resultado_esperado}) ===")
        
        # Actualizar resultado
        if actualizar_resultado_llamada(telefono, escenario):
            # Verificar que se haya actualizado correctamente
            time.sleep(1)  # Pequeña pausa para asegurar que la actualización se complete
            if verificar_resultado_actualizado(telefono, resultado_esperado):
                resultados_pruebas.append(True)
            else:
                resultados_pruebas.append(False)
        else:
            resultados_pruebas.append(False)
    
    # Resumen final
    pruebas_exitosas = resultados_pruebas.count(True)
    pruebas_totales = len(resultados_pruebas)
    
    logger.info("\n=== RESUMEN DE PRUEBAS ===")
    logger.info(f"Total de pruebas: {pruebas_totales}")
    logger.info(f"Pruebas exitosas: {pruebas_exitosas}")
    logger.info(f"Pruebas fallidas: {pruebas_totales - pruebas_exitosas}")
    
    if pruebas_exitosas == pruebas_totales:
        logger.info("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        return True
    else:
        logger.error(f"❌ {pruebas_totales - pruebas_exitosas} PRUEBAS FALLARON")
        return False

if __name__ == "__main__":
    # Permitir cambiar la URL base desde la línea de comandos
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    
    logger.info(f"Usando URL base: {BASE_URL}")
    
    # Ejecutar prueba completa
    resultado = ejecutar_prueba_completa()
    
    # Salir con código de error si alguna prueba falló
    sys.exit(0 if resultado else 1)

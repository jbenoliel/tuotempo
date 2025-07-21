#!/usr/bin/env python
"""
Script para actualizar el estado del lead de JOHANA MARIBEL a "cita convertida"
utilizando la API de actualizar_resultado.
"""

import requests
import json
import logging
import os
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def actualizar_lead_johana():
    """Actualiza el lead de JOHANA MARIBEL a cita convertida"""
    print("\n" + "="*60)
    print("ACTUALIZACIÓN DE LEAD: JOHANA MARIBEL - CITA CONVERTIDA")
    print("="*60)
    
    # Datos del lead
    telefono = "666899514"
    nombre = "JOHANA MARIBEL"
    
    # URLs de la API en Railway
    urls = [
        "https://tuotempo-apis-production.up.railway.app",
        "https://actualizarllamadas.up.railway.app",
        "http://localhost:5000"  # Fallback local para pruebas
    ]
    
    # Endpoint para actualizar resultado
    endpoint_path = "/api/actualizar_resultado"
    
    # Datos para la actualización
    payload = {
        "telefono": telefono,
        "nuevaCita": "25/07/2025",  # La fecha de la cita en formato DD/MM/YYYY
        "conPack": True,  # Asumimos que es con pack, cambiar a False si no lo es
        "horaCita": "10:30",   # Formato HH:MM
        "resultado_llamada": "cita con pack",  # Valor del enum en la base de datos
        "status_level_1": "Éxito",
        "status_level_2": "Cita programada"
    }
    
    print(f"Datos a enviar: {json.dumps(payload, indent=2)}")
    
    # Intentar con cada URL en la lista
    for i, base_url in enumerate(urls):
        endpoint = f"{base_url}{endpoint_path}"
        try:
            print(f"\nIntento {i+1}/{len(urls)}: {endpoint}")
            response = requests.post(endpoint, json=payload, timeout=10)
            
            # Verificar la respuesta
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Actualización exitosa en {base_url}:")
                print(json.dumps(result, indent=2))
                return True
            else:
                print(f"⚠️ Error (Código {response.status_code}):")
                try:
                    error_text = response.json()
                    print(json.dumps(error_text, indent=2))
                except:
                    print(response.text)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error de conexión: {e}")
    
    # Si llegamos aquí, todos los intentos fallaron
    print("\n❌ Error: No se pudo actualizar el lead en ninguna de las APIs disponibles.")
    return False
    
if __name__ == "__main__":
    actualizar_lead_johana()
    print("\nProceso finalizado.")

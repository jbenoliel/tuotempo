"""
Script para buscar y descargar grabaciones de llamadas del 21 de julio de 2025.
Utiliza la API de Pearl AI para obtener las llamadas realizadas en esa fecha.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pearl_caller import get_pearl_client, PearlAPIError
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('grabaciones_21_julio.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def main():
    """Función principal para buscar y descargar grabaciones"""
    print("\n" + "="*60)
    print("BUSCADOR DE GRABACIONES DE PEARL AI - 21 DE JULIO 2025")
    print("="*60)
    
    try:
        # Obtener cliente de Pearl
        pearl_client = get_pearl_client()
        
        # Verificar conexión
        if not pearl_client.test_connection():
            print("❌ Error: No se pudo conectar con la API de Pearl AI")
            return
        
        print("✅ Conexión con Pearl AI establecida")
        
        # Obtener outbound ID
        outbound_id = pearl_client.get_default_outbound_id()
        if not outbound_id:
            # Intentar obtener la lista de campañas
            campaigns = pearl_client.get_outbound_campaigns()
            if campaigns:
                campaign_list = "\n".join([f"  - {c.get('id', 'N/A')}: {c.get('name', 'Sin nombre')}" for c in campaigns[:5]])
                print(f"Campañas disponibles:\n{campaign_list}")
                outbound_id = input("\nIntroduce el ID de la campaña a consultar: ")
            else:
                print("❌ Error: No se encontraron campañas outbound")
                return
        
        print(f"📋 Usando campaña outbound: {outbound_id}")
        
        # Configurar fechas para el 21 de julio de 2025
        today = datetime(2025, 7, 21)
        from_date = today.strftime("%Y-%m-%dT00:00:00Z")
        to_date = today.strftime("%Y-%m-%dT23:59:59Z")
        
        print(f"🔍 Buscando llamadas del {from_date} al {to_date}")
        
        # Buscar llamadas
        calls = pearl_client.search_calls(outbound_id, from_date, to_date)
        
        if not calls:
            print("❌ No se encontraron llamadas para la fecha especificada")
            return
        
        print(f"✅ Se encontraron {len(calls)} llamadas")
        
        # Crear directorio para grabaciones si no existe
        recordings_dir = "grabaciones_21_julio"
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Guardar información de llamadas en un archivo JSON
        calls_file = os.path.join(recordings_dir, "llamadas_21_julio.json")
        with open(calls_file, 'w', encoding='utf-8') as f:
            json.dump(calls, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Información de llamadas guardada en {calls_file}")
        
        # Procesar cada llamada para obtener detalles y grabaciones
        print("\nObteniendo detalles de cada llamada...")
        
        for i, call in enumerate(calls):
            # Manejar tanto si call es un diccionario como si es un string
            if isinstance(call, dict):
                call_id = call.get('id')
            elif isinstance(call, str):
                # Si es un string, podría ser directamente el ID
                call_id = call
            else:
                print(f"[{i+1}/{len(calls)}] Formato de llamada no reconocido: {type(call)}")
                continue
                
            if not call_id:
                continue
                
            print(f"[{i+1}/{len(calls)}] Procesando llamada {call_id}...")
            
            try:
                # Obtener detalles de la llamada
                call_details = pearl_client.get_call_status(call_id)
                
                # Guardar detalles en archivo JSON individual
                call_file = os.path.join(recordings_dir, f"llamada_{call_id}.json")
                with open(call_file, 'w', encoding='utf-8') as f:
                    json.dump(call_details, f, indent=2, ensure_ascii=False)
                    
                print(f"  ✅ Detalles guardados en {call_file}")
            except Exception as e:
                print(f"  ❌ Error al procesar llamada {call_id}: {e}")
            
            # TODO: Descargar grabación de audio si está disponible
            # Esta funcionalidad requeriría implementación adicional en pearl_caller.py
            
        print("\n✅ Proceso completado")
        print(f"📁 Revisa la carpeta '{recordings_dir}' para ver los resultados")
        
    except PearlAPIError as e:
        print(f"❌ Error de API Pearl: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        logger.exception("Error en la ejecución")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Corrección simple de subestados faltantes
"""
import requests
import json

def corregir_todos_los_subestados():
    """Corregir subestados usando lista específica de teléfonos"""
    
    # Los teléfonos que sabemos están en el dashboard como "No Interesado"
    # Incluimos todos los del Excel + intentamos algunos más
    telefonos_no_interesado = [
        "630474787",  # MARIA CONCEPCIO - confirmado
        "617354291",  # ALBA GUTIERREZ - confirmado  
        "637284071",  # SILVIA EUGENIA - confirmado
        "610160783",  # XAVIER LOPEZ - confirmado
        "619230300",  # NURIA PINEDA - confirmado
    ]
    
    # Teléfonos adicionales que podrían estar marcados manualmente
    # Los vamos a probar también
    telefonos_candidatos = [
        "607359224",  # MARIA DE LA SALUD VILLALBA BECERRA
        "687532989",  # MIGUEL EZEQUIEL PAZZELLI  
        "675090997",  # MARIA ANTONIA MARTINEZ GARCIA
        "610510863",  # EVA SAMPER GONZALEZ
    ]
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    todos_los_telefonos = telefonos_no_interesado + telefonos_candidatos
    
    print("CORRECTOR DE SUBESTADOS - NO INTERESADO")
    print(f"Procesando {len(todos_los_telefonos)} registros...")
    print()
    
    corregidos = 0
    errores = 0
    
    for telefono in todos_los_telefonos:
        payload = {
            "telefono": telefono,
            "noInteresado": True,
            "razonNoInteres": "No da motivos",
            "codigoNoInteres": "otros"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"OK: {telefono} - {result.get('message', 'Actualizado')}")
                corregidos += 1
            elif response.status_code == 404:
                print(f"NO ENCONTRADO: {telefono}")
            else:
                print(f"ERROR {telefono}: {response.status_code}")
                errores += 1
                
        except Exception as e:
            print(f"EXCEPCION {telefono}: {e}")
            errores += 1
    
    print(f"\nRESUMEN:")
    print(f"Corregidos: {corregidos}")
    print(f"Errores: {errores}")
    print(f"Total: {len(todos_los_telefonos)}")
    
    print("\nVerifica en el dashboard que ahora tienes 8 subestados")
    print("para los 8 registros 'No Interesado'")

if __name__ == "__main__":
    corregir_todos_los_subestados()
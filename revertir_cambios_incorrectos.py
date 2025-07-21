#!/usr/bin/env python3
"""
Revertir los 4 registros que cambiamos incorrectamente de "Volver a llamar" a "No Interesado"
"""
import requests
import json

def revertir_registros_incorrectos():
    """Revertir los 4 registros que no debían ser No Interesado"""
    
    # Los 4 registros que cambiamos incorrectamente
    registros_a_revertir = [
        {"telefono": "607359224", "nombre": "MARIA DE LA SALUD VILLALBA BECERRA"},
        {"telefono": "687532989", "nombre": "MIGUEL EZEQUIEL PAZZELLI"},
        {"telefono": "675090997", "nombre": "MARIA ANTONIA MARTINEZ GARCIA"},
        {"telefono": "610510863", "nombre": "EVA SAMPER GONZALEZ"}
    ]
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    print("REVIRTIENDO CAMBIOS INCORRECTOS")
    print("Devolviendo 4 registros a 'Volver a llamar'")
    print()
    
    revertidos = 0
    errores = 0
    
    for registro in registros_a_revertir:
        telefono = registro["telefono"]
        nombre = registro["nombre"]
        
        # Payload para cambiar a "Volver a llamar"
        payload = {
            "telefono": telefono,
            "volverALlamar": True,
            "razonvueltaallamar": "Cliente no disponible - Revertido automaticamente",
            "codigoVolverLlamar": "interrupcion"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"REVERTIDO: {telefono} ({nombre[:30]})")
                revertidos += 1
            else:
                print(f"ERROR {telefono}: {response.status_code}")
                errores += 1
                
        except Exception as e:
            print(f"EXCEPCION {telefono}: {e}")
            errores += 1
    
    print(f"\nRESUMEN REVERSION:")
    print(f"Revertidos: {revertidos}")
    print(f"Errores: {errores}")
    print(f"Total: {len(registros_a_revertir)}")
    
    print(f"\nESTADO FINAL ESPERADO:")
    print(f"- 39 'Volver a llamar' (35 + 4 revertidos)")
    print(f"- 9 'No Interesado' (13 - 4 revertidos)")
    print(f"- Todos con subestados correctos")

if __name__ == "__main__":
    revertir_registros_incorrectos()
#!/usr/bin/env python3
"""
Actualización masiva de la BD para corregir todos los status_level_2 faltantes
"""
import requests
import json
import time

def actualizar_bd_masiva():
    """Actualizar masivamente todos los registros con subestados faltantes"""
    
    print("=== ACTUALIZACIÓN MASIVA DE BD ===")
    print("Este script va a:")
    print("1. Forzar TODOS los 'Volver a llamar' a tener subestado 'no disponible cliente'") 
    print("2. Forzar TODOS los 'No Interesado' a tener subestado 'No da motivos'")
    print("3. Usar un rango amplio de teléfonos para cubrir todos los registros")
    print()
    
    confirm = input("¿CONTINUAR con la actualización masiva? (s/N): ").strip().lower()
    if confirm != 's':
        print("Cancelado.")
        return
    
    # Lista amplia de todos los teléfonos conocidos + algunos patrones comunes
    # Incluir los del Excel + intentar patrones de números españoles
    telefonos_conocidos = [
        # Los 39 del Excel
        "615029152", "639328670", "626076545", "722199350", "639849044",
        "627110683", "636337024", "651601214", "644952789", "633865832",
        "667802395", "695904412", "614219370", "697256462", "613441416",
        "601163669", "644893133", "605619977", "618453789", "695033099",
        "676381044", "675654343", "971794186", "674825835", "641858542",
        "635246531", "722706298", "618953725", "676928583", "639484832",
        "630474787", "617354291", "637284071", "610160783", "619230300",
        "607359224", "687532989", "675090997", "610510863"
    ]
    
    # Generar algunos patrones adicionales de números españoles comunes
    patrones_adicionales = []
    
    # Patrones 6XX (móviles)
    for prefix in ["600", "601", "602", "603", "610", "611", "615", "620", "625", "630", "635", "640", "645", "650", "655", "660", "665", "670", "675", "680", "685", "690", "695"]:
        for suffix in ["000001", "000002", "000003", "999999"]:  # Solo algunos ejemplos
            patrones_adicionales.append(prefix + suffix)
    
    # Patrones 7XX y 9XX
    for prefix in ["700", "710", "720", "900", "910", "920", "950", "970"]:
        for suffix in ["000001", "999999"]:
            patrones_adicionales.append(prefix + suffix)
    
    # Combinar listas (limitamos a 100 números adicionales para no saturar)
    todos_los_telefonos = telefonos_conocidos + patrones_adicionales[:50]
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    print(f"Procesando {len(todos_los_telefonos)} números de teléfono...")
    print("Estrategia: Intentar ambos estados (VL + NO) para cada número")
    print()
    
    volver_llamar_actualizados = 0
    no_interesado_actualizados = 0
    no_encontrados = 0
    errores = 0
    
    for i, telefono in enumerate(todos_los_telefonos, 1):
        print(f"{i:3}/{len(todos_los_telefonos)}: {telefono}")
        
        # Estrategia 1: Intentar como "Volver a llamar"
        payload_vl = {
            "telefono": telefono,
            "volverALlamar": True,
            "razonvueltaallamar": "no disponible cliente - MASIVO",
            "codigoVolverLlamar": "interrupcion"
        }
        
        try:
            response = requests.post(api_url, json=payload_vl, headers=headers, timeout=15)
            if response.status_code == 200:
                volver_llamar_actualizados += 1
                print(f"      VL: OK")
            elif response.status_code == 404:
                # No existe, probar con No Interesado
                payload_no = {
                    "telefono": telefono,
                    "noInteresado": True,
                    "razonNoInteres": "No da motivos - MASIVO", 
                    "codigoNoInteres": "otros"
                }
                
                response2 = requests.post(api_url, json=payload_no, headers=headers, timeout=15)
                if response2.status_code == 200:
                    no_interesado_actualizados += 1
                    print(f"      NO: OK")
                elif response2.status_code == 404:
                    no_encontrados += 1
                    print(f"      --: No existe")
                else:
                    errores += 1
                    print(f"      NO: Error {response2.status_code}")
            else:
                errores += 1
                print(f"      VL: Error {response.status_code}")
                
        except Exception as e:
            errores += 1
            print(f"      EX: {e}")
        
        # Pequeña pausa para no saturar
        if i % 10 == 0:
            time.sleep(1)
    
    print(f"\n=== RESUMEN ACTUALIZACIÓN MASIVA ===")
    print(f"Total procesados: {len(todos_los_telefonos)}")
    print(f"'Volver a llamar' actualizados: {volver_llamar_actualizados}")
    print(f"'No Interesado' actualizados: {no_interesado_actualizados}")
    print(f"No encontrados: {no_encontrados}")
    print(f"Errores: {errores}")
    print()
    print("RESULTADO ESPERADO EN DASHBOARD:")
    print(f"- Todos los registros 'Volver a llamar' deberían tener subestado")
    print(f"- Todos los registros 'No Interesado' deberían tener subestado")
    print()
    print("Si aún faltan subestados, significa que hay registros con")
    print("números de teléfono que no están en nuestra lista.")

if __name__ == "__main__":
    actualizar_bd_masiva()
#!/usr/bin/env python3
"""
Solución final para subestados
"""
import requests
import json

def fix_subestados_final():
    """Última corrección de subestados"""
    
    # Todos los teléfonos del Excel con su estado correcto
    registros = [
        # Los que deben ser "No Interesado" (según JSON del Excel)
        {"tel": "630474787", "estado": "NO", "nombre": "MARIA CONCEPCIO"},
        {"tel": "617354291", "estado": "NO", "nombre": "ALBA GUTIERREZ"},  
        {"tel": "637284071", "estado": "NO", "nombre": "SILVIA EUGENIA"},
        {"tel": "610160783", "estado": "NO", "nombre": "XAVIER LOPEZ"},
        {"tel": "619230300", "estado": "NO", "nombre": "NURIA PINEDA"},
        
        # TODOS los demás deben ser "Volver a llamar"
        {"tel": "615029152", "estado": "VL", "nombre": "PAOLA MONTERO"},
        {"tel": "639328670", "estado": "VL", "nombre": "FRANCISCA JIMENEZ"},
        {"tel": "626076545", "estado": "VL", "nombre": "DOMINGO JESUS"},
        {"tel": "722199350", "estado": "VL", "nombre": "PATRICIA SANTAMARIA"},
        {"tel": "639849044", "estado": "VL", "nombre": "PEDRO MARTINEZ"},
        {"tel": "627110683", "estado": "VL", "nombre": "KEVIN BILALI"},
        {"tel": "636337024", "estado": "VL", "nombre": "MARIA ASUNCION"},
        {"tel": "651601214", "estado": "VL", "nombre": "ANALIA ANDREA"},
        {"tel": "644952789", "estado": "VL", "nombre": "ROGER SENDRA"},
        {"tel": "633865832", "estado": "VL", "nombre": "JULIA CAYUELA"},
        {"tel": "667802395", "estado": "VL", "nombre": "LORENA RODRIGUEZ"},
        {"tel": "695904412", "estado": "VL", "nombre": "FRANCISCO JOSE"},
        {"tel": "614219370", "estado": "VL", "nombre": "ISAMEL ISAZA"},
        {"tel": "697256462", "estado": "VL", "nombre": "ROSA VENTURA"},
        {"tel": "613441416", "estado": "VL", "nombre": "KISSI GICEL"},
        {"tel": "601163669", "estado": "VL", "nombre": "ALBA SAGUILLO"},
        {"tel": "644893133", "estado": "VL", "nombre": "LAURA HIDALGO"},
        {"tel": "605619977", "estado": "VL", "nombre": "MORGAN SINCLAIR"},
        {"tel": "618453789", "estado": "VL", "nombre": "LAURA GOMEZ"},
        {"tel": "695033099", "estado": "VL", "nombre": "MAYRA DE LAS ME"},
        {"tel": "676381044", "estado": "VL", "nombre": "SANDRA MARTINEZ"},
        {"tel": "675654343", "estado": "VL", "nombre": "EVA MARIA"},
        {"tel": "971794186", "estado": "VL", "nombre": "SANDRA SEBASTIAN"},
        {"tel": "674825835", "estado": "VL", "nombre": "PAULA SIMOES"},
        {"tel": "641858542", "estado": "VL", "nombre": "LUZ BELLANETH"},
        {"tel": "635246531", "estado": "VL", "nombre": "IRENE DEL"},
        {"tel": "722706298", "estado": "VL", "nombre": "YAIZA GIMENEZ"},
        {"tel": "618953725", "estado": "VL", "nombre": "CHRISTIAN TRASHORRAS"},
        {"tel": "676928583", "estado": "VL", "nombre": "PAOLA VERONICA"},
        {"tel": "639484832", "estado": "VL", "nombre": "PEDRO ALEXANDER"},
        {"tel": "607359224", "estado": "VL", "nombre": "MARIA DE LA SALUD"},
        {"tel": "687532989", "estado": "VL", "nombre": "MIGUEL EZEQUIEL"},
        {"tel": "675090997", "estado": "VL", "nombre": "MARIA ANTONIA"},
        {"tel": "610510863", "estado": "VL", "nombre": "EVA SAMPER"},
    ]
    
    api_url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    headers = {'Content-Type': 'application/json'}
    
    print("CORRECCIÓN FINAL DE SUBESTADOS")
    print(f"Procesando {len(registros)} registros...")
    
    no_count = 0
    vl_count = 0
    errores = 0
    
    for i, reg in enumerate(registros, 1):
        tel = reg["tel"]
        estado = reg["estado"]
        nombre = reg["nombre"][:25]
        
        if estado == "NO":
            payload = {
                "telefono": tel,
                "noInteresado": True,
                "razonNoInteres": "No da motivos",
                "codigoNoInteres": "otros"
            }
            no_count += 1
        else:  # VL
            payload = {
                "telefono": tel,
                "volverALlamar": True,
                "razonvueltaallamar": "no disponible cliente",
                "codigoVolverLlamar": "interrupcion"
            }
            vl_count += 1
        
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                print(f"{i:2}. OK: {nombre} ({tel}) -> {estado}")
            else:
                print(f"{i:2}. ERROR: {nombre} ({tel}) -> {response.status_code}")
                errores += 1
        except Exception as e:
            print(f"{i:2}. EXCEPTION: {nombre} ({tel}) -> {e}")
            errores += 1
    
    print(f"\nRESUMEN:")
    print(f"No Interesado procesados: {no_count}")
    print(f"Volver a llamar procesados: {vl_count}")
    print(f"Errores: {errores}")
    print(f"Total: {len(registros)}")
    
    print(f"\nDASHBOARD DEBERÍA MOSTRAR:")
    print(f"- {vl_count} 'Volver a llamar' con {vl_count} subestados")
    print(f"- {no_count} 'No Interesado' con {no_count} subestados")

if __name__ == "__main__":
    fix_subestados_final()
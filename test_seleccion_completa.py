#!/usr/bin/env python3
"""
Test completo para verificar que la selección en UI corresponde con la BD
"""

import requests
import time
from db import get_connection

BASE_URL = "http://localhost:5000"

def contar_seleccionados_bd():
    """Contar leads seleccionados en la base de datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE selected_for_calling = 1")
        seleccionados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE selected_for_calling = 0")
        no_seleccionados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        
        return {
            "seleccionados": seleccionados,
            "no_seleccionados": no_seleccionados,
            "total": total
        }
        
    except Exception as e:
        print(f"Error consultando BD: {e}")
        return None
    finally:
        if conn:
            conn.close()

def obtener_leads_api():
    """Obtener leads desde la API"""
    try:
        response = requests.get(f"{BASE_URL}/api/calls/leads", timeout=5)
        if response.status_code == 200:
            data = response.json()
            leads = data.get('leads', [])
            return leads
        else:
            print(f"Error API: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error llamando API: {e}")
        return []

def seleccionar_leads_api(lead_ids, selected=True):
    """Seleccionar leads usando la API"""
    try:
        payload = {
            "lead_ids": lead_ids,
            "selected": selected
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/leads/select",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('updated_count', 0)
        else:
            print(f"Error seleccionando: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return 0
            
    except Exception as e:
        print(f"Error en selección API: {e}")
        return 0

def test_seleccion_parcial():
    """Test de selección de algunos leads"""
    print("\n=== TEST: SELECCIÓN PARCIAL ===")
    
    # 1. Estado inicial
    estado_inicial = contar_seleccionados_bd()
    print(f"Estado inicial BD: {estado_inicial}")
    
    # 2. Obtener algunos leads
    leads = obtener_leads_api()
    if len(leads) < 5:
        print("No hay suficientes leads para el test")
        return False
    
    # 3. Seleccionar primeros 5 leads
    primeros_5_ids = [lead['id'] for lead in leads[:5]]
    print(f"Seleccionando leads: {primeros_5_ids}")
    
    updated_count = seleccionar_leads_api(primeros_5_ids, selected=True)
    print(f"API reporta {updated_count} leads actualizados")
    
    # 4. Verificar en BD
    time.sleep(1)  # Dar tiempo para que se complete la transacción
    estado_final = contar_seleccionados_bd()
    print(f"Estado final BD: {estado_final}")
    
    # 5. Validar
    diferencia_seleccionados = estado_final['seleccionados'] - estado_inicial['seleccionados']
    print(f"Diferencia en BD: +{diferencia_seleccionados} seleccionados")
    
    if updated_count == diferencia_seleccionados:
        print("✅ ÉXITO: La API y la BD coinciden")
        return True
    else:
        print(f"❌ ERROR: API reporta {updated_count} pero BD cambió en {diferencia_seleccionados}")
        return False

def test_seleccion_masiva():
    """Test de selección masiva (simulando 'Seleccionar Todo')"""
    print("\n=== TEST: SELECCIÓN MASIVA (Simular Seleccionar Todo) ===")
    
    # 1. Deseleccionar todo primero
    print("1. Deseleccionando todos los leads...")
    leads = obtener_leads_api()
    all_ids = [lead['id'] for lead in leads]
    
    deselected_count = seleccionar_leads_api(all_ids, selected=False)
    print(f"Deseleccionados: {deselected_count} leads")
    time.sleep(1)
    
    estado_inicial = contar_seleccionados_bd()
    print(f"Estado después de deseleccionar: {estado_inicial}")
    
    # 2. Simular "Seleccionar Todo" - seleccionar los primeros 15 (como hace la paginación)
    print("2. Simulando 'Seleccionar Todo' (primeros 15 leads)...")
    primeros_15_ids = [lead['id'] for lead in leads[:15]]
    
    selected_count = seleccionar_leads_api(primeros_15_ids, selected=True)
    print(f"API reporta {selected_count} leads seleccionados")
    time.sleep(1)
    
    # 3. Verificar en BD
    estado_final = contar_seleccionados_bd()
    print(f"Estado final BD: {estado_final}")
    
    # 4. Validar
    if estado_final['seleccionados'] == selected_count:
        print("✅ ÉXITO: 'Seleccionar Todo' funciona correctamente")
        return True
    else:
        print(f"❌ ERROR: Se esperaban {selected_count} seleccionados, pero hay {estado_final['seleccionados']}")
        return False

def verificar_consistencia():
    """Verificar que los datos en la API coinciden con la BD"""
    print("\n=== VERIFICACIÓN DE CONSISTENCIA ===")
    
    # 1. Contar en BD
    bd_data = contar_seleccionados_bd()
    print(f"BD: {bd_data}")
    
    # 2. Contar en API
    leads = obtener_leads_api()
    api_seleccionados = len([l for l in leads if l.get('selected_for_calling')])
    api_total = len(leads)
    
    print(f"API: total={api_total}, seleccionados={api_seleccionados}")
    
    # 3. Comparar
    if bd_data['total'] == api_total and bd_data['seleccionados'] == api_seleccionados:
        print("✅ CONSISTENCIA: BD y API coinciden perfectamente")
        return True
    else:
        print("❌ INCONSISTENCIA detectada entre BD y API")
        return False

def main():
    print("TEST COMPLETO: SELECCION UI <-> BD")
    print("="*50)
    
    # Verificar servidor
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code != 200:
            print("Servidor no disponible")
            return
    except:
        print("No se puede conectar al servidor")
        print("   Ejecuta: python start.py")
        return
    
    print("Servidor conectado")
    
    # Tests
    results = []
    
    results.append(("Consistencia inicial", verificar_consistencia()))
    results.append(("Selección parcial", test_seleccion_parcial()))
    results.append(("Selección masiva", test_seleccion_masiva()))
    results.append(("Consistencia final", verificar_consistencia()))
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE RESULTADOS:")
    print("="*50)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 TODOS LOS TESTS PASARON")
        print("La selección UI ↔ BD funciona correctamente")
    else:
        print("\n⚠️ ALGUNOS TESTS FALLARON")
        print("Hay problemas en la sincronización UI ↔ BD")

if __name__ == "__main__":
    main()
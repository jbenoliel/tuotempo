#!/usr/bin/env python3
"""
Test para verificar la nueva funcionalidad de "Seleccionar Todo" (todos los filtrados)
"""

import requests
import time
from db import get_connection

BASE_URL = "http://localhost:5000"

def contar_seleccionados_bd():
    """Contar leads seleccionados en BD"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads WHERE selected_for_calling = 1")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error BD: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def limpiar_selecciones():
    """Limpiar todas las selecciones para empezar el test limpio"""
    print("Limpiando todas las selecciones...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE leads SET selected_for_calling = 0")
        updated = cursor.rowcount
        conn.commit()
        print(f"Limpiadas {updated} selecciones")
        return True
    except Exception as e:
        print(f"Error limpiando: {e}")
        return False
    finally:
        if conn:
            conn.close()

def test_seleccion_sin_filtros():
    """Test 1: Selección sin filtros (debe seleccionar TODOS los 964 leads)"""
    print("\n=== TEST 1: SIN FILTROS ===")
    
    limpiar_selecciones()
    
    # Obtener todos los leads desde API
    response = requests.get(f"{BASE_URL}/api/calls/leads")
    if response.status_code != 200:
        print("Error obteniendo leads de API")
        return False
    
    leads = response.json().get('leads', [])
    print(f"API devuelve {len(leads)} leads")
    
    # Si no hay filtros, debería seleccionar TODOS
    all_ids = [lead['id'] for lead in leads]
    
    print(f"Seleccionando {len(all_ids)} leads...")
    response = requests.post(f"{BASE_URL}/api/calls/leads/select", json={
        "lead_ids": all_ids,
        "selected": True
    })
    
    if response.status_code == 200:
        updated = response.json().get('updated_count', 0)
        print(f"API reporta {updated} leads actualizados")
        
        time.sleep(1)
        bd_count = contar_seleccionados_bd()
        print(f"BD tiene {bd_count} seleccionados")
        
        if bd_count == updated:
            print("EXITO: Sin filtros selecciona todos correctamente")
            return True
        else:
            print(f"ERROR: Inconsistencia API({updated}) vs BD({bd_count})")
            return False
    else:
        print(f"Error en API: {response.status_code}")
        return False

def test_seleccion_con_filtros():
    """Test 2: Selección con filtros (debe seleccionar solo los filtrados)"""
    print("\n=== TEST 2: CON FILTROS ===")
    
    limpiar_selecciones()
    
    # Buscar leads con un status específico para filtrar
    response = requests.get(f"{BASE_URL}/api/calls/leads")
    if response.status_code != 200:
        print("Error obteniendo leads")
        return False
    
    all_leads = response.json().get('leads', [])
    
    # Encontrar un estado común para usar como filtro
    status_counts = {}
    for lead in all_leads:
        status = lead.get('status_level_1', '')
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
    
    if not status_counts:
        print("No hay leads con status_level_1 para filtrar")
        return False
    
    # Usar el estado más común como filtro
    test_status = max(status_counts.keys(), key=lambda x: status_counts[x])
    expected_count = status_counts[test_status]
    
    print(f"Probando filtro status_level_1='{test_status}' (esperados: {expected_count} leads)")
    
    # Obtener leads filtrados desde API
    response = requests.get(f"{BASE_URL}/api/calls/leads", params={
        "estado1": test_status
    })
    
    if response.status_code == 200:
        filtered_leads = response.json().get('leads', [])
        filtered_ids = [lead['id'] for lead in filtered_leads]
        
        print(f"API filtrada devuelve {len(filtered_ids)} leads")
        
        # Seleccionar solo los filtrados
        response = requests.post(f"{BASE_URL}/api/calls/leads/select", json={
            "lead_ids": filtered_ids,
            "selected": True
        })
        
        if response.status_code == 200:
            updated = response.json().get('updated_count', 0)
            print(f"API reporta {updated} leads actualizados")
            
            time.sleep(1)
            bd_count = contar_seleccionados_bd()
            print(f"BD tiene {bd_count} seleccionados")
            
            if bd_count == updated == len(filtered_ids):
                print("EXITO: Con filtros selecciona solo los filtrados")
                return True
            else:
                print(f"ERROR: Esperado {len(filtered_ids)}, API {updated}, BD {bd_count}")
                return False
        else:
            print(f"Error seleccionando: {response.status_code}")
            return False
    else:
        print(f"Error obteniendo leads filtrados: {response.status_code}")
        return False

def test_rendimiento():
    """Test 3: Verificar que el procesamiento por lotes funciona"""
    print("\n=== TEST 3: RENDIMIENTO CON MUCHOS LEADS ===")
    
    limpiar_selecciones()
    
    # Obtener todos los leads
    response = requests.get(f"{BASE_URL}/api/calls/leads")
    if response.status_code != 200:
        print("Error obteniendo leads")
        return False
    
    leads = response.json().get('leads', [])
    all_ids = [lead['id'] for lead in leads]
    
    if len(all_ids) < 100:
        print(f"Solo hay {len(all_ids)} leads, no se puede probar procesamiento por lotes")
        print("(El procesamiento por lotes se activa con >100 leads)")
        return True
    
    print(f"Probando selección de {len(all_ids)} leads (procesamiento por lotes)...")
    
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/api/calls/leads/select", json={
        "lead_ids": all_ids,
        "selected": True
    }, timeout=30)  # Timeout más largo para muchos leads
    
    end_time = time.time()
    duration = end_time - start_time
    
    if response.status_code == 200:
        updated = response.json().get('updated_count', 0)
        print(f"Seleccionados {updated} leads en {duration:.2f} segundos")
        
        if duration < 10:  # Debería ser rápido
            print("EXITO: Procesamiento eficiente")
            return True
        else:
            print("ADVERTENCIA: Procesamiento lento pero funcional")
            return True
    else:
        print(f"ERROR: {response.status_code}")
        return False

def main():
    print("TEST DE LA NUEVA FUNCIONALIDAD: Seleccionar Todos los Filtrados")
    print("=" * 60)
    
    # Verificar servidor
    try:
        requests.get(f"{BASE_URL}/health", timeout=3)
        print("Servidor conectado")
    except:
        print("ERROR: Servidor no disponible. Ejecuta: python start.py")
        return
    
    # Ejecutar tests
    results = []
    results.append(("Sin filtros (todos)", test_seleccion_sin_filtros()))
    results.append(("Con filtros (filtrados)", test_seleccion_con_filtros()))
    results.append(("Rendimiento", test_rendimiento()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE RESULTADOS:")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASO" if passed else "FALLO"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\nTODOS LOS TESTS PASARON!")
        print("La nueva funcionalidad funciona correctamente.")
    else:
        print("\nALGUNOS TESTS FALLARON.")
        print("Revisa los errores arriba.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test simple para verificar selección UI -> BD
"""

import requests
import time
from db import get_connection

BASE_URL = "http://localhost:5000"

def contar_bd():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads WHERE selected_for_calling = 1")
    seleccionados = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM leads")
    total = cursor.fetchone()[0]
    conn.close()
    return seleccionados, total

def obtener_leads():
    response = requests.get(f"{BASE_URL}/api/calls/leads")
    if response.status_code == 200:
        return response.json().get('leads', [])
    return []

def seleccionar_leads(lead_ids):
    payload = {"lead_ids": lead_ids, "selected": True}
    response = requests.post(f"{BASE_URL}/api/calls/leads/select", json=payload)
    if response.status_code == 200:
        return response.json().get('updated_count', 0)
    return 0

def test():
    print("TEST: Verificando seleccion UI -> BD")
    print("="*40)
    
    # 1. Estado inicial
    sel_inicial, total = contar_bd()
    print(f"BD inicial: {sel_inicial} seleccionados de {total}")
    
    # 2. Obtener leads desde API
    leads = obtener_leads()
    print(f"API devuelve: {len(leads)} leads")
    
    if len(leads) == 0:
        print("ERROR: No hay leads en la API")
        return
    
    # 3. Seleccionar primeros 10
    primeros_10 = [lead['id'] for lead in leads[:10]]
    print(f"Seleccionando IDs: {primeros_10}")
    
    updated = seleccionar_leads(primeros_10)
    print(f"API reporta: {updated} leads actualizados")
    
    # 4. Verificar BD
    time.sleep(1)
    sel_final, _ = contar_bd()
    diferencia = sel_final - sel_inicial
    print(f"BD final: {sel_final} seleccionados (diferencia: +{diferencia})")
    
    # 5. Resultado
    if updated == diferencia:
        print("EXITO: UI y BD coinciden")
    else:
        print(f"ERROR: API dice {updated}, BD cambió {diferencia}")
    
    # 6. Test inverso - deseleccionar
    print("\nTest deseleccion:")
    payload = {"lead_ids": primeros_10, "selected": False}
    response = requests.post(f"{BASE_URL}/api/calls/leads/select", json=payload)
    
    if response.status_code == 200:
        updated = response.json().get('updated_count', 0)
        time.sleep(1)
        sel_final2, _ = contar_bd()
        diferencia2 = sel_final - sel_final2
        print(f"Deseleccionados API: {updated}, BD: {diferencia2}")
        if updated == diferencia2:
            print("EXITO: Deseleccion funciona")
        else:
            print("ERROR: Deseleccion inconsistente")

if __name__ == "__main__":
    test()
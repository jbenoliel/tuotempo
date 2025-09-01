#!/usr/bin/env python3
"""
Test definitivo para verificar si se solucionó el problema de selección
"""

import requests
import time

BASE_URL = "http://localhost:5000"

def verificar_servidor():
    """Verificar que el servidor esté funcionando"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code == 200:
            print("✅ Servidor funcionando")
            return True
        else:
            print(f"❌ Servidor responde con error: {response.status_code}")
            return False
    except:
        print("❌ No se puede conectar al servidor")
        print("   Ejecuta: python start.py")
        return False

def obtener_leads():
    """Obtener leads del servidor"""
    try:
        response = requests.get(f"{BASE_URL}/api/calls/leads", timeout=5)
        if response.status_code == 200:
            data = response.json()
            leads = data.get('leads', [])
            print(f"✅ Obtenidos {len(leads)} leads del servidor")
            return leads
        else:
            print(f"❌ Error obteniendo leads: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def probar_seleccion(lead_ids):
    """Probar la selección de leads"""
    if not lead_ids:
        print("❌ No hay leads para probar")
        return False
        
    try:
        # Seleccionar algunos leads
        response = requests.post(
            f"{BASE_URL}/api/calls/leads/select",
            json={"lead_ids": lead_ids[:3], "selected": True},
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ API de selección funciona correctamente")
            return True
        else:
            print(f"❌ Error en selección: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error probando selección: {e}")
        return False

def main():
    print("🧪 PRUEBA DEFINITIVA - PROBLEMA DE SELECCIÓN")
    print("=" * 50)
    
    # 1. Verificar servidor
    if not verificar_servidor():
        return
    
    # 2. Obtener leads
    leads = obtener_leads()
    if not leads:
        print("⚠️ No hay leads en la base de datos")
        print("   Necesitas cargar algunos leads primero")
        return
    
    # 3. Probar selección
    lead_ids = [lead['id'] for lead in leads]
    if probar_seleccion(lead_ids):
        print("\n🎉 BACKEND FUNCIONA CORRECTAMENTE!")
    else:
        print("\n❌ Problema en el backend")
        return
    
    # 4. Instrucciones para UI
    print("\n" + "="*50)
    print("📋 INSTRUCCIONES PARA PROBAR LA UI:")
    print("="*50)
    print("1. Abre: http://localhost:5000/calls-manager")
    print("2. Abre DevTools (F12) y ve a la pestaña Console")
    print("3. Haz clic en 'Seleccionar Todo'")
    print("4. Observa la consola - deberías ver logs como:")
    print("   🔥 [DEBUG] selectAllLeads iniciado - selected=true")
    print("   🔥 [DEBUG] Leads filtrados: X")
    print("   🔥 [DEBUG] Leads paginados: X")
    print("5. Si los leads desaparecen, revisa si dice:")
    print("   🔥 [DEBUG] ❌ NO HAY LEADS FILTRADOS")
    print("\n💡 Si sigue fallando, el problema puede ser:")
    print("   - Filtros automáticos activándose")
    print("   - Problema en getFilteredLeads()")
    print("   - Estado de leads no actualizándose correctamente")
    
    print(f"\n📊 DATOS ACTUALES:")
    print(f"   - Total leads disponibles: {len(leads)}")
    print(f"   - Endpoint backend: {BASE_URL}/api/calls/leads/select")
    print(f"   - Estado: ✅ Funcionando")

if __name__ == "__main__":
    main()
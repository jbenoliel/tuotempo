#!/usr/bin/env python3
"""
Test que simula exactamente lo que hace el frontend calls-manager
"""

import requests
import json

def test_frontend_calls():
    """Simula las llamadas que hace el frontend"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 === SIMULANDO LLAMADAS DEL FRONTEND ===")
    
    # 1. Test de configuración (la primera llamada que hace el frontend)
    print("\n1. Probando GET /api/calls/configuration")
    try:
        response = requests.get(f"{base_url}/api/calls/configuration")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Configuración: {data.get('configuration')}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Test de estado del sistema
    print("\n2. Probando GET /api/calls/status")
    try:
        response = requests.get(f"{base_url}/api/calls/status")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Estado: {data.get('success')}")
            print(f"   📊 Leads summary: {data.get('leads_summary')}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Test de leads (la llamada principal)
    print("\n3. Probando GET /api/calls/leads")
    try:
        response = requests.get(f"{base_url}/api/calls/leads")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            leads = data.get('leads', [])
            pagination = data.get('pagination', {})
            
            print(f"   ✅ Success: {data.get('success')}")
            print(f"   📊 Total leads: {pagination.get('total')}")
            print(f"   📋 Leads devueltos: {len(leads)}")
            
            if leads:
                print(f"\n   📝 Primer lead completo:")
                first_lead = leads[0]
                for key, value in first_lead.items():
                    print(f"     {key}: {value}")
                
                # Verificar campos críticos que usa el frontend
                critical_fields = ['id', 'nombre', 'telefono', 'ciudad', 'call_status']
                print(f"\n   🔍 Campos críticos:")
                for field in critical_fields:
                    value = first_lead.get(field)
                    status = "✅" if value is not None else "❌"
                    print(f"     {status} {field}: {value}")
            else:
                print("   ❌ No se devolvieron leads")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Test con parámetros específicos
    print("\n4. Probando GET /api/calls/leads con parámetros")
    try:
        params = {
            'limit': 50,
            'offset': 0
        }
        response = requests.get(f"{base_url}/api/calls/leads", params=params)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Con parámetros: {len(data.get('leads', []))} leads")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def verify_frontend_expectations():
    """Verifica que los datos cumplan las expectativas del frontend"""
    
    print("\n🔍 === VERIFICANDO EXPECTATIVAS DEL FRONTEND ===")
    
    try:
        response = requests.get("http://localhost:5000/api/calls/leads")
        if response.status_code != 200:
            print("❌ API no disponible")
            return
        
        data = response.json()
        leads = data.get('leads', [])
        
        if not leads:
            print("❌ No hay leads para verificar")
            return
        
        lead = leads[0]
        
        # Campos que espera el frontend (según el createLeadRow)
        expected_fields = {
            'id': 'number',
            'nombre': 'string', 
            'telefono': 'string',
            'ciudad': 'string',
            'nombre_clinica': 'string',
            'call_status': 'string',
            'call_priority': 'number',
            'call_attempts_count': 'number',
            'last_call_attempt': 'string or null',
            'selected_for_calling': 'boolean'
        }
        
        print("🧪 Verificando campos esperados por el frontend:")
        all_good = True
        
        for field, expected_type in expected_fields.items():
            value = lead.get(field)
            
            if value is None and 'null' not in expected_type:
                print(f"   ❌ {field}: FALTA (esperado: {expected_type})")
                all_good = False
            else:
                print(f"   ✅ {field}: {value} ({type(value).__name__})")
        
        if all_good:
            print("\n🎉 ¡Todos los campos esperados están presentes!")
        else:
            print("\n⚠️ Algunos campos faltan. Esto podría causar problemas en el frontend.")
        
        # Verificar estructura de respuesta
        print(f"\n📋 Estructura completa de respuesta:")
        print(f"   success: {data.get('success')}")
        print(f"   leads: array de {len(leads)} elementos")
        print(f"   pagination: {data.get('pagination')}")
        print(f"   timestamp: {data.get('timestamp')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_frontend_calls()
    verify_frontend_expectations()
    
    print(f"\n💡 PRÓXIMOS PASOS:")
    print("1. Abre la página calls-manager")
    print("2. Abre la consola del navegador (F12)")
    print("3. Busca errores en la consola")
    print("4. Ve a Network y verifica las peticiones")
    print("5. Si ves la petición a /api/calls/leads, verifica su respuesta")

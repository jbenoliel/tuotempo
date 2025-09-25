#!/usr/bin/env python3
"""
Consultar a través de la API local los leads cerrados de septiembre
"""

import requests
import json

def consultar_api_leads_cerrados():
    """Usar la API local para investigar leads cerrados"""
    base_url = "http://localhost:5000"

    print("=== CONSULTANDO API LOCAL PARA LEADS CERRADOS ===")

    # 1. Consultar estadísticas generales de leads
    try:
        print("\n1. Consultando estadísticas de leads...")
        response = requests.get(f"{base_url}/api/calls/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total leads: {stats.get('total_leads', 'N/A')}")
            print(f"   Leads abiertos: {stats.get('open_leads', 'N/A')}")
            print(f"   Leads cerrados: {stats.get('closed_leads', 'N/A')}")
        else:
            print(f"   Error: {response.status_code}")
    except Exception as e:
        print(f"   Error consultando stats: {e}")

    # 2. Intentar obtener leads con filtros específicos
    try:
        print("\n2. Consultando leads con filtros...")
        # Parámetros para leads de septiembre con estado "Volver a llamar"
        params = {
            'page': 1,
            'per_page': 100,
            'estado1': 'Volver a llamar',
            'origen_archivo': 'Septiembre'
        }

        response = requests.get(f"{base_url}/api/leads", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            leads = data.get('data', [])
            total = data.get('total', 0)

            print(f"   Total leads encontrados: {total}")
            print(f"   Leads en esta página: {len(leads)}")

            if leads:
                # Analizar los primeros leads
                abiertos = sum(1 for lead in leads if lead.get('lead_status') in [None, 'open'])
                cerrados = len(leads) - abiertos

                print(f"   En esta muestra:")
                print(f"     - Abiertos: {abiertos}")
                print(f"     - Cerrados: {cerrados}")

                # Mostrar ejemplos de cerrados
                cerrados_ejemplos = [lead for lead in leads if lead.get('lead_status') not in [None, 'open']][:5]
                if cerrados_ejemplos:
                    print(f"   Ejemplos de leads cerrados:")
                    for lead in cerrados_ejemplos:
                        nombre = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}".strip() or 'Sin nombre'
                        print(f"     - ID {lead.get('id')}: {nombre}")
                        print(f"       Lead_status: {lead.get('lead_status')}")
                        print(f"       Status_level_2: {lead.get('status_level_2')}")
                        print(f"       Call_attempts: {lead.get('call_attempts', 0)}")
                        print()
        else:
            print(f"   Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   Error consultando leads: {e}")

    print("\n=== CONCLUSIÓN ===")
    print("Si hay muchos leads cerrados con 'Volver a llamar', verifica:")
    print("1. ¿Status_level_2 indica 'Cita Agendada' o 'Cita Manual'?")
    print("2. ¿Call_attempts indica máximo de llamadas alcanzado?")
    print("3. ¿Lead_status cambió a 'No Interesado' por alguna razón?")

if __name__ == "__main__":
    consultar_api_leads_cerrados()
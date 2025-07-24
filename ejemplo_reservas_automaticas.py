#!/usr/bin/env python3
"""
Ejemplo de uso de la API de Reservas Automáticas
===============================================

Este script muestra cómo usar la API actualizada para marcar leads
para reservas automáticas con diferentes configuraciones.

Ejemplos incluidos:
1. Marcar lead para reserva automática con valores por defecto
2. Marcar lead con preferencia de tarde y fecha específica
3. Actualizar resultado de llamada y marcar para reserva automática
4. Consultar leads marcados para reserva automática
"""

import requests
import json
from datetime import datetime, date, timedelta

# Configuración de la API
API_BASE_URL = "http://localhost:5000"  # Ajustar según tu configuración
# API_BASE_URL = "https://tuotempo-apis-production.up.railway.app"  # Para producción

def ejemplo_reserva_automatica_basica():
    """
    Ejemplo 1: Marcar lead para reserva automática con valores por defecto
    - Preferencia: mañana (por defecto)
    - Fecha mínima: hoy + 15 días (por defecto)
    """
    print("=== Ejemplo 1: Reserva automática básica ===")
    
    url = f"{API_BASE_URL}/api/actualizar_resultado"
    
    data = {
        "telefono": "612345678",
        "reservaAutomatica": True
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def ejemplo_reserva_automatica_personalizada():
    """
    Ejemplo 2: Marcar lead con preferencia de tarde y fecha específica
    """
    print("=== Ejemplo 2: Reserva automática personalizada ===")
    
    url = f"{API_BASE_URL}/api/actualizar_resultado"
    
    # Fecha específica (en 7 días)
    fecha_minima = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    
    data = {
        "telefono": "612345679",
        "reservaAutomatica": True,
        "preferenciaHorario": "tarde",
        "fechaMinimaReserva": fecha_minima
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def ejemplo_resultado_llamada_con_reserva():
    """
    Ejemplo 3: Actualizar resultado de llamada y marcar para reserva automática
    """
    print("=== Ejemplo 3: Resultado de llamada + reserva automática ===")
    
    url = f"{API_BASE_URL}/api/actualizar_resultado"
    
    data = {
        "telefono": "612345680",
        "volverALlamar": True,
        "codigoVolverLlamar": "interrupcion",
        "reservaAutomatica": True,
        "preferenciaHorario": "mañana",
        "fechaMinimaReserva": "30/07/2024"
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def ejemplo_desmarcar_reserva_automatica():
    """
    Ejemplo 4: Desmarcar lead de reserva automática
    """
    print("=== Ejemplo 4: Desmarcar reserva automática ===")
    
    url = f"{API_BASE_URL}/api/actualizar_resultado"
    
    data = {
        "telefono": "612345678",
        "reservaAutomatica": False
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def consultar_leads_reserva_automatica():
    """
    Ejemplo 5: Consultar leads marcados para reserva automática
    (Requiere crear un endpoint adicional para consultas)
    """
    print("=== Ejemplo 5: Consultar leads con reserva automática ===")
    
    # Este sería un endpoint adicional que podrías crear
    url = f"{API_BASE_URL}/api/leads_reserva_automatica"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            leads = response.json()
            print(f"Leads marcados para reserva automática: {len(leads.get('leads', []))}")
            
            for lead in leads.get('leads', [])[:3]:  # Mostrar solo los primeros 3
                print(f"- {lead.get('nombre')} {lead.get('apellidos')} ({lead.get('telefono')})")
                print(f"  Preferencia: {lead.get('preferencia_horario')}")
                print(f"  Fecha mínima: {lead.get('fecha_minima_reserva')}")
        else:
            print(f"Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Endpoint no disponible aún: {e}")
    
    print()

def ejemplo_cita_con_reserva_automatica():
    """
    Ejemplo 6: Programar cita y marcar para reserva automática futura
    """
    print("=== Ejemplo 6: Cita programada + reserva automática futura ===")
    
    url = f"{API_BASE_URL}/api/actualizar_resultado"
    
    data = {
        "telefono": "612345681",
        "nuevaCita": "28/07/2024",
        "horaCita": "10:30",
        "conPack": True,
        # Marcar para una segunda cita automática en el futuro
        "reservaAutomatica": True,
        "preferenciaHorario": "tarde",
        "fechaMinimaReserva": "15/08/2024"  # Un mes después
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def ejemplo_formatos_fecha():
    """
    Ejemplo 7: Diferentes formatos de fecha soportados
    """
    print("=== Ejemplo 7: Diferentes formatos de fecha ===")
    
    url = f"{API_BASE_URL}/api/actualizar_resultado"
    
    # Formato DD/MM/YYYY
    data1 = {
        "telefono": "612345682",
        "reservaAutomatica": True,
        "fechaMinimaReserva": "25/07/2024"
    }
    
    # Formato YYYY-MM-DD
    data2 = {
        "telefono": "612345683",
        "reservaAutomatica": True,
        "fechaMinimaReserva": "2024-07-25"
    }
    
    for i, data in enumerate([data1, data2], 1):
        response = requests.post(url, json=data)
        print(f"Formato {i} - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    
    print()

def main():
    """Ejecutar todos los ejemplos"""
    print("Ejemplos de uso de la API de Reservas Automáticas")
    print("=" * 50)
    print()
    
    try:
        ejemplo_reserva_automatica_basica()
        ejemplo_reserva_automatica_personalizada()
        ejemplo_resultado_llamada_con_reserva()
        ejemplo_desmarcar_reserva_automatica()
        consultar_leads_reserva_automatica()
        ejemplo_cita_con_reserva_automatica()
        ejemplo_formatos_fecha()
        
        print("Todos los ejemplos ejecutados correctamente!")
        
    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar a la API. Asegúrate de que el servidor esté ejecutándose.")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    main()

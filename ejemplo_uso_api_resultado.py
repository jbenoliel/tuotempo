import requests
import json
from datetime import datetime

# URL base de la API - Ajusta según tu configuración
API_BASE_URL = "http://localhost:5001/api"

def verificar_estado():
    """Verifica si la API está en línea"""
    try:
        response = requests.get(f"{API_BASE_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"API en línea: {data['timestamp']}")
            return True
        else:
            print(f"Error al verificar estado: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def actualizar_resultado_llamada(telefono, cita=None, con_pack=False, no_interesado=False):
    """
    Actualiza el resultado de una llamada según los parámetros
    
    Args:
        telefono (str): Número de teléfono del contacto
        cita (str, optional): Fecha y hora de la cita (formato YYYY-MM-DD HH:MM:SS)
        con_pack (bool, optional): Si la cita incluye pack
        no_interesado (bool, optional): Si el contacto no está interesado
        
    Returns:
        dict: Respuesta de la API
    """
    url = f"{API_BASE_URL}/actualizar_resultado"
    
    # Preparar datos
    data = {
        "telefono": telefono,
        "no_interesado": no_interesado
    }
    
    if cita:
        data["cita"] = cita
        data["conPack"] = con_pack
    
    # Hacer la solicitud
    try:
        response = requests.post(url, json=data)
        result = response.json()
        
        if response.status_code == 200:
            print(f"✅ Resultado actualizado: {result['resultado']} para {telefono}")
        else:
            print(f"❌ Error: {result.get('error', 'Desconocido')}")
        
        return result
    except Exception as e:
        print(f"Error de conexión: {e}")
        return {"error": str(e)}

def obtener_contactos(filtro_resultado=None):
    """
    Obtiene la lista de contactos con un filtro opcional de resultado
    
    Args:
        filtro_resultado (str, optional): Filtro por resultado de llamada
        
    Returns:
        list: Lista de contactos
    """
    url = f"{API_BASE_URL}/obtener_resultados"
    params = {}
    
    if filtro_resultado:
        params["resultado"] = filtro_resultado
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"Se encontraron {data['count']} contactos")
            
            # Mostrar resumen de contactos
            for contacto in data.get("contactos", []):
                print(f"- {contacto.get('nombre', '')} {contacto.get('apellidos', '')}")
                print(f"  Tel: {contacto.get('telefono', '')}")
                print(f"  Resultado: {contacto.get('resultado_llamada', 'No definido')}")
                if contacto.get('cita'):
                    pack_str = "Con pack" if contacto.get('conPack') else "Sin pack"
                    print(f"  Cita: {contacto['cita']} ({pack_str})")
                print()
                
            return data.get("contactos", [])
        else:
            print(f"Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error de conexión: {e}")
        return []

def main():
    """Función principal para demostrar el uso de la API"""
    print("DEMO API RESULTADO LLAMADA")
    print("==========================")
    
    # Verificar estado de la API
    if not verificar_estado():
        print("La API no está disponible. Verifique que esté en ejecución.")
        return
    
    print("\nEjemplos de actualización de resultados:")
    
    # Ejemplo 1: Contacto con cita y pack
    print("\n1. Contacto que toma cita con pack:")
    fecha_cita = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    actualizar_resultado_llamada(
        telefono="600123456",
        cita=fecha_cita,
        con_pack=True
    )
    
    # Ejemplo 2: Contacto con cita sin pack
    print("\n2. Contacto que toma cita sin pack:")
    actualizar_resultado_llamada(
        telefono="600789012",
        cita=fecha_cita,
        con_pack=False
    )
    
    # Ejemplo 3: Contacto no interesado
    print("\n3. Contacto no interesado:")
    actualizar_resultado_llamada(
        telefono="600456789",
        no_interesado=True
    )
    
    # Ejemplo 4: Llamada cortada (volver a marcar)
    print("\n4. Llamada cortada (volver a marcar):")
    actualizar_resultado_llamada(
        telefono="600345678"
    )
    
    # Consultar resultados
    print("\nContactos con cita con pack:")
    obtener_contactos(filtro_resultado="cita con pack")
    
    print("\nContactos con cita sin pack:")
    obtener_contactos(filtro_resultado="cita sin pack")
    
    print("\nContactos no interesados:")
    obtener_contactos(filtro_resultado="no interesado")
    
    print("\nContactos para volver a marcar:")
    obtener_contactos(filtro_resultado="volver a marcar")

if __name__ == "__main__":
    main()

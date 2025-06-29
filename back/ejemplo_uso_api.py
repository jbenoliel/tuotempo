import requests
import json
from datetime import datetime, timedelta

# URL base de la API (ajustar si es necesario)
BASE_URL = "http://localhost:5000/api"

def verificar_estado():
    """Verificar si la API está funcionando"""
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            print("API en línea:", response.json())
            return True
        else:
            print(f"Error al verificar estado: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def buscar_clinica_por_telefono(telefono):
    """Buscar una clínica por su número de teléfono"""
    try:
        response = requests.get(f"{BASE_URL}/clinica", params={"telefono": telefono})
        if response.status_code == 200:
            print("Clínica encontrada:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return response.json()
        elif response.status_code == 404:
            print(f"No se encontró clínica con el teléfono {telefono}")
            return None
        else:
            print(f"Error al buscar clínica: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

def actualizar_cita(telefono, fecha_cita=None, con_pack=None, estado=None):
    """Actualizar información de cita para un número de teléfono"""
    data = {"telefono": telefono}
    
    if fecha_cita:
        data["cita"] = fecha_cita
    
    if con_pack is not None:
        data["conPack"] = con_pack
    
    if estado:
        data["estado"] = estado
    
    try:
        response = requests.post(f"{BASE_URL}/update_cita", json=data)
        if response.status_code == 200:
            print("Actualización exitosa:", response.json())
            return True
        else:
            print(f"Error al actualizar: {response.status_code}")
            print(response.json())
            return False
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def listar_clinicas(filtro_estado=None, filtro_con_pack=None):
    """Listar todas las clínicas con filtros opcionales"""
    params = {}
    if filtro_estado:
        params["estado"] = filtro_estado
    
    if filtro_con_pack is not None:
        params["conPack"] = "true" if filtro_con_pack else "false"
    
    try:
        response = requests.get(f"{BASE_URL}/clinicas", params=params)
        if response.status_code == 200:
            clinicas = response.json()
            print(f"Se encontraron {len(clinicas)} clínicas")
            for i, clinica in enumerate(clinicas[:5], 1):  # Mostrar solo las primeras 5
                print(f"{i}. {clinica.get('nombre_clinica')} - Tel: {clinica.get('telefono')}")
                print(f"   Cita: {clinica.get('cita', 'No programada')}")
                print(f"   Estado: {clinica.get('ultimo_estado', 'No definido')}")
                print(f"   Con Pack: {'Sí' if clinica.get('conPack') else 'No'}")
                print("---")
            
            if len(clinicas) > 5:
                print(f"... y {len(clinicas) - 5} más")
            
            return clinicas
        else:
            print(f"Error al listar clínicas: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

def demo():
    """Ejecutar una demostración de uso de la API"""
    print("=== DEMO DE USO DE LA API DE CITAS ===")
    
    # Verificar estado de la API
    if not verificar_estado():
        print("La API no está disponible. Asegúrate de que esté en ejecución.")
        return
    
    # Ejemplo 1: Buscar clínica por teléfono
    print("\n=== EJEMPLO 1: BUSCAR CLÍNICA POR TELÉFONO ===")
    telefono = "91 955 19 00"  # Usar un teléfono que exista en tu base de datos
    clinica = buscar_clinica_por_telefono(telefono)
    
    if not clinica:
        print("No se pudo continuar con la demostración. Verifica el número de teléfono.")
        return
    
    # Ejemplo 2: Actualizar cita
    print("\n=== EJEMPLO 2: ACTUALIZAR CITA ===")
    # Crear fecha de cita para mañana a las 10:00
    manana = datetime.now() + timedelta(days=1)
    fecha_cita = manana.replace(hour=10, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    
    actualizar_cita(
        telefono=telefono,
        fecha_cita=fecha_cita,
        con_pack=True,
        estado="no answer"
    )
    
    # Verificar la actualización
    print("\nVerificando la actualización:")
    buscar_clinica_por_telefono(telefono)
    
    # Ejemplo 3: Listar clínicas con filtros
    print("\n=== EJEMPLO 3: LISTAR CLÍNICAS CON FILTROS ===")
    print("\nClínicas con estado 'no answer':")
    listar_clinicas(filtro_estado="no answer")
    
    print("\nClínicas con pack:")
    listar_clinicas(filtro_con_pack=True)
    
    print("\n=== FIN DE LA DEMOSTRACIÓN ===")

if __name__ == "__main__":
    demo()

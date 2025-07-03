import pandas as pd
import sys
import json
from tuotempo_api import TuoTempoAPI

def buscar_centros_por_cp(codigo_postal=None):
    """
    Busca centros por código postal y los exporta a Excel
    
    Args:
        codigo_postal (str): Código postal a buscar. Si es None, muestra todos los centros.
    
    Returns:
        tuple: (éxito, mensaje, ruta_archivo)
    """
    # Crear instancia de la API (ajusta los parámetros si es necesario)
    api = TuoTempoAPI(lang='es', environment='PRE')
    
    print(f"Buscando centros{' para CP: ' + codigo_postal if codigo_postal else ''}...")
    
    # Obtener todos los centros (sin filtro de provincia)
    centers_response = api.get_centers(province=None)
    
    if centers_response.get("result") != "OK":
        error_msg = f"Error al obtener centros: {centers_response.get('message', 'Error desconocido')}"
        print(error_msg)
        return False, error_msg, None
    
    # Extrae la lista de centros desde la clave correcta
    centers_list = centers_response.get('return', {}).get('results', [])
    
    if not centers_list:
        error_msg = "No se encontraron centros en la respuesta de la API"
        print(error_msg)
        return False, error_msg, None
    
    # Filtrar solo las columnas requeridas
    campos = [
        'areaid',
        'areaTitle',
        'address',
        'cp',
        'city',
        'province',
        'phone'
    ]
    
    # Extraer solo los campos seleccionados
    datos_filtrados = []
    for centro in centers_list:
        if not isinstance(centro, dict):
            continue  # Salta elementos que no sean diccionarios
            
        # Si se especificó un código postal, filtrar por él
        if codigo_postal and str(centro.get('cp', '')).strip() != str(codigo_postal).strip():
            continue
            
        fila = {campo: centro.get(campo, '') for campo in campos}
        datos_filtrados.append(fila)
    
    # Crear DataFrame con los datos filtrados
    df = pd.DataFrame(datos_filtrados)
    
    if df.empty:
        error_msg = f"No se encontraron centros{' para el código postal ' + codigo_postal if codigo_postal else ''}"
        print(error_msg)
        return False, error_msg, None
    
    # Generar nombre de archivo
    if codigo_postal:
        output_path = f'centros_cp_{codigo_postal}.xlsx'
    else:
        output_path = 'todos_los_centros.xlsx'
    
    # Exportar a Excel
    df.to_excel(output_path, index=False)
    
    success_msg = f"¡{len(df)} centros encontrados y exportados a {output_path}!"
    print(success_msg)
    
    # Mostrar los primeros 5 centros encontrados
    print("\nPrimeros centros encontrados:")
    for i, (_, centro) in enumerate(df.head(5).iterrows(), 1):
        print(f"{i}. {centro['areaTitle']} - {centro['address']}, {centro['city']} ({centro['cp']})")
    
    if len(df) > 5:
        print(f"... y {len(df) - 5} centros más.")
    
    return True, success_msg, output_path

if __name__ == "__main__":
    # Si se proporciona un código postal como argumento, usarlo
    if len(sys.argv) > 1:
        codigo_postal = sys.argv[1]
        buscar_centros_por_cp(codigo_postal)
    else:
        # Solicitar código postal al usuario
        codigo_postal = input("Introduce el código postal a buscar (deja en blanco para ver todos): ").strip()
        if codigo_postal:
            buscar_centros_por_cp(codigo_postal)
        else:
            buscar_centros_por_cp()

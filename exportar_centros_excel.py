import pandas as pd
from tuotempo_api import TuoTempoAPI

# Crear instancia de la API (ajusta los parámetros si es necesario)
api = TuoTempoAPI(lang='es', environment='PRE')

# Obtener todos los centros (sin filtro de provincia)
centers_response = api.get_centers(province=None)

# Imprimir la estructura para depuración
print("Tipo de respuesta:", type(centers_response))
print("Respuesta completa:", centers_response)

# Extrae la lista de centros desde la clave correcta
centers_list = None
if isinstance(centers_response, dict):
    # Según el ejemplo, la clave parece ser 'members', que contiene una lista de diccionarios
    for key, value in centers_response.items():
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            print(f"Detectada lista de centros en la clave '{key}'")
            centers_list = value
            break
    # Si no se detecta, prueba con la clave 'members' explícitamente
    if centers_list is None and 'return' in centers_response:
        centers_list = centers_response['return']

if centers_list is not None:
    # Si centers_list es un dict y tiene la clave 'results', usa esa lista
    if isinstance(centers_list, dict) and 'results' in centers_list:
        centers_list = centers_list['results']
    # Filtrar solo las columnas requeridas
    campos = [
        'areaid',
        'areaTitle',
        'address',
        'cp',
        'city',
        'province'
    ]
    # Extraer solo los campos seleccionados
    datos_filtrados = []
    for centro in centers_list:
        if not isinstance(centro, dict):
            continue  # Salta elementos que no sean diccionarios
        fila = {campo: centro.get(campo, '') for campo in campos}
        datos_filtrados.append(fila)
    df = pd.DataFrame(datos_filtrados)
    output_path = 'centros_exportados.xlsx'
    df.to_excel(output_path, index=False)
    print(f"¡Centros exportados correctamente a {output_path}!")
    print(f"Centros válidos exportados: {len(df)}")
    if len(df) == 0:
        print("La lista de centros filtrados está vacía. Mostrando información cruda de centers_list:")
        print(f"Tipo de centers_list: {type(centers_list)}")
        if isinstance(centers_list, list):
            print(centers_list[:2])
        elif isinstance(centers_list, dict):
            print(f"Claves: {list(centers_list.keys())}")
            # Muestra el primer elemento si alguna clave contiene una lista
            for k, v in centers_list.items():
                if isinstance(v, list) and len(v) > 0:
                    print(f"Primer elemento de la clave '{k}': {v[0]}")
                    break
            else:
                print("No se encontró ninguna lista dentro del diccionario.")
        else:
            print(centers_list)
else:
    print("No se pudo extraer la lista de centros automáticamente. Claves disponibles:")
    print(list(centers_response.keys()))

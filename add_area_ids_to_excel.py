import requests
import pandas as pd
import os
import json
import re
from fuzzywuzzy import process, fuzz

def get_areas(instance_id="tt_portal_adeslas", lang="es"):
    """Obtiene todas las áreas/centros de TuoTempo"""
    url = f"https://app.tuotempo.com/api/v3/{instance_id}/areas"
    headers = {"content-type": "application/json; charset=UTF-8"}
    params = {"lang": lang}
    
    print(f"Obteniendo áreas desde: {url}")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Guardar la respuesta completa para referencia
        with open('areas_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Depurar la estructura de la respuesta
        print("Estructura de la respuesta:")
        print(f"Tipo de datos: {type(data)}")
        print(f"Claves principales: {list(data.keys()) if isinstance(data, dict) else 'No es un diccionario'}")
        
        # Manejar diferentes formatos de respuesta
        areas = []
        if isinstance(data, dict):
            if "return" in data:
                ret_data = data["return"]
                if isinstance(ret_data, dict) and "results" in ret_data:
                    results = ret_data["results"]
                    if isinstance(results, dict) and "areas" in results:
                        areas = results["areas"]
                    elif isinstance(results, list):
                        # Algunos endpoints devuelven directamente una lista
                        areas = results
                elif isinstance(ret_data, list):
                    # Algunos endpoints devuelven la lista directamente en "return"
                    areas = ret_data
            elif "results" in data:
                # Formato alternativo donde "results" está en el nivel superior
                results = data["results"]
                if isinstance(results, dict) and "areas" in results:
                    areas = results["areas"]
                elif isinstance(results, list):
                    areas = results
            elif "areas" in data:
                # Formato donde "areas" está en el nivel superior
                areas = data["areas"]
        elif isinstance(data, list):
            # La respuesta es directamente una lista
            areas = data
        
        if not isinstance(areas, list):
            print(f"Error: No se pudo extraer una lista de áreas. Tipo obtenido: {type(areas)}")
            return []
            
        print(f"Se encontraron {len(areas)} áreas/centros")
        return areas
    except Exception as e:
        print(f"Error al obtener áreas: {e}")
        return []

def normalize_address(address):
    """
    Normaliza una dirección eliminando código postal, ciudad y normalizando abreviaturas
    """
    if not address or not isinstance(address, str):
        return ""
        
    # Convertir a minúsculas y eliminar puntos
    address = address.lower().replace(".", "").strip()
    
    # Normalizar abreviaturas de vías
    address = address.replace("c/ ", "calle ")
    address = address.replace("cl ", "calle ")
    address = address.replace("avda ", "avenida ")
    address = address.replace("av ", "avenida ")
    address = address.replace("pza ", "plaza ")
    address = address.replace("pl ", "plaza ")
    address = address.replace("ps ", "paseo ")
    address = address.replace("p° ", "paseo ")
    
    # Eliminar código postal (formato español: 5 dígitos)
    address = re.sub(r'\b\d{5}\b', '', address)
    
    # Eliminar nombres de ciudades comunes
    cities = ["madrid", "barcelona", "valencia", "sevilla", "zaragoza", "malaga", "murcia", 
             "palma", "bilbao", "alicante", "cordoba", "valladolid", "vigo", "gijon"]
    
    for city in cities:
        address = re.sub(r'\b' + city + r'\b', '', address, flags=re.IGNORECASE)
    
    # Eliminar múltiples espacios
    address = re.sub(r'\s+', ' ', address).strip()
    
    # Eliminar comas al final
    address = address.rstrip(",")
    
    return address

def find_best_match(search_text, choices_dict, min_score=70):
    """
    Encuentra la mejor coincidencia para un texto en un diccionario de opciones
    usando coincidencia difusa (fuzzy matching) y normalización de direcciones
    """
    if not search_text or not isinstance(search_text, str):
        return None
    
    # Normalizar el texto de búsqueda
    normalized_search = normalize_address(search_text)
    if not normalized_search:
        return None
    
    # Normalizar todas las claves del diccionario
    normalized_choices = {}
    for key, value in choices_dict.items():
        if key:
            normalized_key = normalize_address(key)
            normalized_choices[normalized_key] = value
    
    # Buscar coincidencia exacta primero con texto normalizado
    if normalized_search in normalized_choices:
        return normalized_choices[normalized_search]
    
    # Si no hay coincidencia exacta, usar coincidencia difusa con texto normalizado
    choices = list(normalized_choices.keys())
    best_match = process.extractOne(normalized_search, choices, scorer=fuzz.token_sort_ratio)
    
    if best_match and best_match[1] >= min_score:
        return normalized_choices[best_match[0]]
    
    return None

def main():
    # Ruta del archivo Excel
    excel_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\01NP Dental_Piloto_VoiceBot_20250603_TeYame.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"Error: No se encuentra el archivo Excel en {excel_path}")
        return
    
    # Leer el Excel
    print(f"Leyendo archivo Excel: {excel_path}")
    try:
        df = pd.read_excel(excel_path)
        print(f"Excel cargado correctamente. Filas: {len(df)}, Columnas: {list(df.columns)}")
        
        # Mostrar las primeras filas para entender la estructura
        print("\nPrimeras 3 filas del Excel:")
        print(df.head(3).to_string())
    except Exception as e:
        print(f"Error al leer el Excel: {e}")
        return
    
    # Obtener todas las áreas
    areas = get_areas()
    if not areas:
        print("No se pudieron obtener las áreas. Verificar la conexión o el endpoint.")
        return
    
    # Mostrar ejemplos de áreas
    # print("\nEjemplos de áreas disponibles en TuoTempo:")
    # for i, area in enumerate(areas[:5]):
    #     print(f"  {i+1}. {area.get('areaTitle', 'N/A')} - ID: {area.get('areaid', 'N/A')}")
    #     print(f"     Dirección: {area.get('address', 'No disponible')}")
    
    # Crear diccionarios para búsqueda rápida
    areas_by_address = {a.get("address", "").strip().lower(): a.get("areaid") for a in areas if a.get("address")}
    areas_by_name = {a.get("areaTitle", "").strip().lower(): a.get("areaid") for a in areas if a.get("areaTitle")}
    
    # Crear un diccionario de áreas por nombre parcial (para búsqueda más flexible)
    areas_by_partial_name = {}
    for area in areas:
        if area.get("areaTitle"):
            name = area.get("areaTitle").strip()
            # Guardar palabras clave del nombre
            words = name.lower().split()
            for word in words:
                if len(word) > 3:  # Solo palabras significativas
                    if word not in areas_by_partial_name:
                        areas_by_partial_name[word] = []
                    areas_by_partial_name[word].append(area.get("areaid"))
    
    # Mapeo de nombres de columnas posibles
    address_columns = ["DIRECCION_CLINICA", "Dirección", "Direccion", "DIRECCIÓN", "DIRECCION", "Address", "CENTRO DIRECCIÓN", "CENTRO DIRECCION"]
    name_columns = ["NOMBRE_CLINICA", "Clínica", "Clinica", "CLÍNICA", "CLINICA", "Centro", "CENTRO", "Nombre", "NOMBRE", "Name"]
    
    # Encontrar las columnas correctas en el Excel
    address_col = None
    for col in address_columns:
        if col in df.columns:
            address_col = col
            break
    
    name_col = None
    for col in name_columns:
        if col in df.columns:
            name_col = col
            break
    
    # Si no encontramos las columnas estándar, intentar inferir cuáles podrían contener la información
    if not address_col and not name_col:
        print("\nNo se encontraron columnas estándar de dirección o nombre.")
        print("Analizando columnas disponibles para encontrar posibles coincidencias...")
        
        # Mostrar todas las columnas para que el usuario pueda elegir
        print("\nColumnas disponibles en el Excel:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}. {col}")
        
        # Intentar usar columnas que podrían contener información relevante
        for col in df.columns:
            if "CENTRO" in col.upper() or "CLINI" in col.upper() or "DENTAL" in col.upper():
                name_col = col
                print(f"\nUsando columna '{col}' como posible nombre de clínica")
                break
    
    # Función para buscar el areaId para cada fila
    def find_area_id(row):
        area_id = None
        match_source = ""
        match_confidence = 0
        
        # Buscar por dirección si existe la columna
        if address_col and pd.notna(row.get(address_col)):
            direccion = str(row[address_col]).strip()
            area_id = find_best_match(direccion, areas_by_address)
            if area_id:
                return area_id, "dirección exacta", 100
            
            # Intentar búsqueda parcial por dirección
            for addr_key in areas_by_address.keys():
                if len(direccion) > 5 and direccion.lower() in addr_key:
                    return areas_by_address[addr_key], "dirección parcial", 90
                elif len(addr_key) > 5 and addr_key in direccion.lower():
                    return areas_by_address[addr_key], "dirección parcial", 80
        
        # Buscar por nombre si existe la columna
        if name_col and pd.notna(row.get(name_col)):
            nombre = str(row[name_col]).strip()
            
            # Buscar coincidencia exacta
            area_id = find_best_match(nombre, areas_by_name)
            if area_id:
                return area_id, "nombre exacto", 100
            
            # Buscar coincidencia parcial
            for name_key in areas_by_name.keys():
                if len(nombre) > 5 and nombre.lower() in name_key:
                    return areas_by_name[name_key], "nombre parcial", 90
                elif len(name_key) > 5 and name_key in nombre.lower():
                    return areas_by_name[name_key], "nombre parcial", 80
            
            # Buscar por palabras clave
            words = nombre.lower().split()
            for word in words:
                if len(word) > 3 and word in areas_by_partial_name:
                    # Si hay múltiples coincidencias, devolver la primera
                    if areas_by_partial_name[word]:
                        return areas_by_partial_name[word][0], f"palabra clave '{word}'", 70
        
        # Si llegamos aquí, no se encontró coincidencia
        return "", "sin coincidencia", 0
    
    # Añadir las columnas de resultado
    print("Añadiendo columnas al Excel...")
    
    # Aplicar la función de búsqueda y desempaquetar los resultados
    results = df.apply(find_area_id, axis=1)
    
    # Crear nuevas columnas a partir de los resultados
    df["areaId"] = results.apply(lambda x: x[0] if isinstance(x, tuple) and len(x) > 0 else "")
    df["match_source"] = results.apply(lambda x: x[1] if isinstance(x, tuple) and len(x) > 1 else "")
    df["match_confidence"] = results.apply(lambda x: x[2] if isinstance(x, tuple) and len(x) > 2 else 0)
    
    # Contar cuántas filas tienen areaId
    matched_rows = (df["areaId"] != "").sum()
    print(f"Se encontraron coincidencias para {matched_rows} de {len(df)} filas")
    
    # Mostrar estadísticas por tipo de coincidencia
    if matched_rows > 0:
        print("\nEstadísticas por tipo de coincidencia:")
        match_stats = df["match_source"].value_counts()
        for source, count in match_stats.items():
            print(f"  - {source}: {count} coincidencias ({count/len(df)*100:.1f}%)")
    
    # Guardar el resultado
    output_path = excel_path.replace(".xlsx", "_con_areaId.xlsx")
    df.to_excel(output_path, index=False)
    print(f"\nArchivo guardado en: {output_path}")
    
    # Mostrar algunos ejemplos
    print("\nEjemplos de coincidencias:")
    # Tomar algunas muestras con coincidencia y algunas sin coincidencia
    samples_with_match = df[df["areaId"] != ""].head(3)
    samples_without_match = df[df["areaId"] == ""].head(2)
    sample = pd.concat([samples_with_match, samples_without_match])
    
    for _, row in sample.iterrows():
        address = row.get(address_col, "N/A") if address_col else "N/A"
        name = row.get(name_col, "N/A") if name_col else "N/A"
        area_id = row.get("areaId", "")
        match_source = row.get("match_source", "")
        confidence = row.get("match_confidence", 0)
        
        match_status = "✓" if area_id else "✗"
        print(f"{match_status} {name} - {address} -> areaId: {area_id} ({match_source}, confianza: {confidence}%)")
    
    print("\nRevisa el archivo Excel generado para ver todas las coincidencias.")
    print("Si hay muchas filas sin coincidencia, considera ajustar el algoritmo de búsqueda.")
    print("También puedes revisar 'areas_response.json' para ver todos los centros disponibles.")
    

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Programa para encontrar areaId de clínicas basándose en nombre y dirección desde un Excel.

Este programa:
1. Lee un archivo Excel con información de clínicas
2. Obtiene todas las áreas/centros disponibles de TuoTempo
3. Busca coincidencias por nombre y dirección usando fuzzy matching
4. Genera un nuevo Excel con los areaId encontrados

Uso:
    python buscar_areaid_excel.py --excel "ruta/al/archivo.xlsx" --nombre "NOMBRE_CLINICA" --direccion "DIRECCION_CLINICA"
    
Ejemplo:
    python buscar_areaid_excel.py --excel "clinicas.xlsx" --nombre "NOMBRE_CLINICA" --direccion "DIRECCION_CLINICA"
"""

import requests
import pandas as pd
import os
import json
import re
import argparse
from fuzzywuzzy import process, fuzz
from datetime import datetime

def get_areas(instance_id="tt_portal_adeslas", lang="es"):
    """Obtiene todas las áreas/centros de TuoTempo"""
    url = f"https://app.tuotempo.com/api/v3/{instance_id}/areas"
    headers = {"content-type": "application/json; charset=UTF-8"}
    params = {"lang": lang}
    
    print(f"🔍 Obteniendo áreas desde TuoTempo...")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Guardar la respuesta completa para referencia
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f'areas_response_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
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
                        areas = results
                elif isinstance(ret_data, list):
                    areas = ret_data
            elif "results" in data:
                results = data["results"]
                if isinstance(results, dict) and "areas" in results:
                    areas = results["areas"]
                elif isinstance(results, list):
                    areas = results
            elif "areas" in data:
                areas = data["areas"]
        elif isinstance(data, list):
            areas = data
        
        if not isinstance(areas, list):
            print(f"❌ Error: No se pudo extraer una lista de áreas. Tipo obtenido: {type(areas)}")
            return []
            
        print(f"✅ Se encontraron {len(areas)} áreas/centros disponibles")
        return areas
    except Exception as e:
        print(f"❌ Error al obtener áreas: {e}")
        return []

def normalize_address(address):
    """Normaliza una dirección eliminando código postal, ciudad y normalizando abreviaturas"""
    if not address or not isinstance(address, str):
        return ""
        
    # Convertir a minúsculas y eliminar puntos
    address = address.lower().replace(".", "").strip()
    
    # Normalizar abreviaturas de vías
    replacements = {
        "c/ ": "calle ", "cl ": "calle ", "c ": "calle ",
        "avda ": "avenida ", "av ": "avenida ", "avd ": "avenida ",
        "pza ": "plaza ", "pl ": "plaza ", "plz ": "plaza ",
        "ps ": "paseo ", "p° ": "paseo ", "pº ": "paseo ",
        "ctra ": "carretera ", "carr ": "carretera ",
        "urb ": "urbanización ", "pol ": "polígono "
    }
    
    for old, new in replacements.items():
        address = address.replace(old, new)
    
    # Eliminar código postal (formato español: 5 dígitos)
    address = re.sub(r'\b\d{5}\b', '', address)
    
    # Eliminar nombres de ciudades comunes
    cities = ["madrid", "barcelona", "valencia", "sevilla", "zaragoza", "málaga", "murcia", 
             "palma", "bilbao", "alicante", "córdoba", "valladolid", "vigo", "gijón",
             "hospitalet", "vitoria", "granada", "elche", "oviedo", "badalona", "cartagena",
             "terrassa", "jerez", "sabadell", "móstoles", "santa", "alcalá", "pamplona"]
    
    for city in cities:
        address = re.sub(r'\b' + city + r'\b', '', address, flags=re.IGNORECASE)
    
    # Eliminar múltiples espacios y comas
    address = re.sub(r'\s+', ' ', address).strip()
    address = re.sub(r',+', ',', address).strip(',')
    
    return address

def find_best_match(search_text, choices_dict, min_score=70):
    """Encuentra la mejor coincidencia usando fuzzy matching"""
    if not search_text or not choices_dict:
        return None
        
    # Usar fuzzywuzzy para encontrar la mejor coincidencia
    result = process.extractOne(search_text, choices_dict.keys(), scorer=fuzz.ratio)
    
    if result and result[1] >= min_score:
        return choices_dict[result[0]]
    
    return None

def process_excel(excel_path, name_col, address_col, output_path=None):
    """Procesa el archivo Excel y añade los areaId"""
    
    # Verificar que el archivo existe
    if not os.path.exists(excel_path):
        print(f"❌ Error: No se encontró el archivo {excel_path}")
        return False
    
    print(f"📖 Leyendo archivo Excel: {excel_path}")
    
    try:
        # Leer el Excel
        df = pd.read_excel(excel_path)
        print(f"✅ Archivo leído correctamente. {len(df)} filas encontradas")
        
        # Verificar que las columnas existen
        if name_col and name_col not in df.columns:
            print(f"❌ Error: La columna '{name_col}' no existe en el Excel")
            print(f"Columnas disponibles: {list(df.columns)}")
            return False
            
        if address_col and address_col not in df.columns:
            print(f"❌ Error: La columna '{address_col}' no existe en el Excel")
            print(f"Columnas disponibles: {list(df.columns)}")
            return False
        
    except Exception as e:
        print(f"❌ Error al leer el Excel: {e}")
        return False
    
    # Obtener áreas de TuoTempo
    areas = get_areas()
    if not areas:
        print("❌ No se pudieron obtener las áreas de TuoTempo")
        return False
    
    # Crear diccionarios de búsqueda
    print("🔧 Preparando índices de búsqueda...")
    areas_by_address = {}
    areas_by_name = {}
    areas_by_partial_name = {}
    
    for area in areas:
        # Por dirección
        if area.get("address"):
            normalized_addr = normalize_address(area["address"])
            if normalized_addr:
                areas_by_address[normalized_addr] = area.get("areaid")
        
        # Por nombre
        if area.get("areaTitle"):
            normalized_name = area["areaTitle"].strip().lower()
            areas_by_name[normalized_name] = area.get("areaid")
            
            # Por palabras clave del nombre
            words = normalized_name.split()
            for word in words:
                if len(word) > 3:  # Solo palabras de más de 3 caracteres
                    if word not in areas_by_partial_name:
                        areas_by_partial_name[word] = []
                    areas_by_partial_name[word].append(area.get("areaid"))
    
    print(f"✅ Índices creados: {len(areas_by_address)} direcciones, {len(areas_by_name)} nombres")
    
    def find_area_id(row):
        """Encuentra el areaId para una fila del Excel"""
        
        # Buscar por dirección si existe la columna
        if address_col and pd.notna(row.get(address_col)):
            direccion = str(row[address_col]).strip()
            normalized_dir = normalize_address(direccion)
            
            # Buscar coincidencia exacta
            area_id = find_best_match(normalized_dir, areas_by_address, min_score=80)
            if area_id:
                return area_id, "dirección exacta", 100
            
            # Buscar coincidencia parcial
            for addr_key in areas_by_address.keys():
                if len(normalized_dir) > 5 and normalized_dir in addr_key:
                    return areas_by_address[addr_key], "dirección parcial", 90
                elif len(addr_key) > 5 and addr_key in normalized_dir:
                    return areas_by_address[addr_key], "dirección parcial", 80
        
        # Buscar por nombre si existe la columna
        if name_col and pd.notna(row.get(name_col)):
            nombre = str(row[name_col]).strip()
            normalized_name = nombre.lower()
            
            # Buscar coincidencia exacta
            area_id = find_best_match(normalized_name, areas_by_name, min_score=80)
            if area_id:
                return area_id, "nombre exacto", 100
            
            # Buscar coincidencia parcial
            for name_key in areas_by_name.keys():
                if len(normalized_name) > 5 and normalized_name in name_key:
                    return areas_by_name[name_key], "nombre parcial", 90
                elif len(name_key) > 5 and name_key in normalized_name:
                    return areas_by_name[name_key], "nombre parcial", 80
            
            # Buscar por palabras clave
            words = normalized_name.split()
            for word in words:
                if len(word) > 3 and word in areas_by_partial_name:
                    if areas_by_partial_name[word]:
                        return areas_by_partial_name[word][0], f"palabra clave '{word}'", 70
        
        # Si llegamos aquí, no se encontró coincidencia
        return "", "sin coincidencia", 0
    
    # Aplicar la búsqueda
    print("🔍 Buscando coincidencias...")
    results = df.apply(find_area_id, axis=1)
    
    # Crear nuevas columnas
    df["areaId"] = results.apply(lambda x: x[0] if isinstance(x, tuple) and len(x) > 0 else "")
    df["match_source"] = results.apply(lambda x: x[1] if isinstance(x, tuple) and len(x) > 1 else "")
    df["match_confidence"] = results.apply(lambda x: x[2] if isinstance(x, tuple) and len(x) > 2 else 0)
    
    # Estadísticas
    matched_rows = (df["areaId"] != "").sum()
    print(f"✅ Se encontraron coincidencias para {matched_rows} de {len(df)} filas ({matched_rows/len(df)*100:.1f}%)")
    
    if matched_rows > 0:
        print("\n📊 Estadísticas por tipo de coincidencia:")
        match_stats = df["match_source"].value_counts()
        for source, count in match_stats.items():
            if source != "sin coincidencia":
                print(f"  ✓ {source}: {count} coincidencias ({count/len(df)*100:.1f}%)")
        
        # Mostrar estadísticas de confianza
        confidence_stats = df[df["areaId"] != ""]["match_confidence"].describe()
        print(f"\n🎯 Confianza promedio: {confidence_stats['mean']:.1f}%")
        print(f"   Confianza mínima: {confidence_stats['min']:.1f}%")
        print(f"   Confianza máxima: {confidence_stats['max']:.1f}%")
    
    # Guardar resultado
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = excel_path.replace(".xlsx", f"_con_areaId_{timestamp}.xlsx")
    
    df.to_excel(output_path, index=False)
    print(f"\n💾 Archivo guardado en: {output_path}")
    
    # Mostrar ejemplos
    print("\n📋 Ejemplos de resultados:")
    samples_with_match = df[df["areaId"] != ""].head(3)
    samples_without_match = df[df["areaId"] == ""].head(2)
    sample = pd.concat([samples_with_match, samples_without_match])
    
    for _, row in sample.iterrows():
        address = row.get(address_col, "N/A") if address_col else "N/A"
        name = row.get(name_col, "N/A") if name_col else "N/A"
        area_id = row.get("areaId", "")
        match_source = row.get("match_source", "")
        confidence = row.get("match_confidence", 0)
        
        match_status = "✅" if area_id else "❌"
        print(f"{match_status} {name[:30]:<30} | {address[:30]:<30} | areaId: {area_id[:20]:<20} | {match_source} ({confidence}%)")
    
    print(f"\n🎉 Proceso completado. Revisa el archivo: {output_path}")
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Buscar areaId de clínicas en un Excel basándose en nombre y dirección",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python buscar_areaid_excel.py --excel "clinicas.xlsx" --nombre "NOMBRE_CLINICA" --direccion "DIRECCION_CLINICA"
  python buscar_areaid_excel.py --excel "datos.xlsx" --nombre "Nombre" --direccion "Dirección" --output "resultado.xlsx"
  python buscar_areaid_excel.py --excel "clinicas.xlsx" --nombre "CLINICA"  # Solo por nombre
  python buscar_areaid_excel.py --excel "clinicas.xlsx" --direccion "DIRECCION"  # Solo por dirección
        """
    )
    
    parser.add_argument("--excel", required=True, help="Ruta al archivo Excel de entrada")
    parser.add_argument("--nombre", help="Nombre de la columna que contiene el nombre de la clínica")
    parser.add_argument("--direccion", help="Nombre de la columna que contiene la dirección de la clínica")
    parser.add_argument("--output", help="Ruta del archivo Excel de salida (opcional)")
    parser.add_argument("--instance", default="tt_portal_adeslas", help="Instance ID de TuoTempo (default: tt_portal_adeslas)")
    
    args = parser.parse_args()
    
    # Validar que al menos una columna esté especificada
    if not args.nombre and not args.direccion:
        print("❌ Error: Debes especificar al menos --nombre o --direccion")
        parser.print_help()
        return
    
    print("🚀 Iniciando búsqueda de areaId en Excel...")
    print(f"📁 Archivo: {args.excel}")
    if args.nombre:
        print(f"👤 Columna nombre: {args.nombre}")
    if args.direccion:
        print(f"📍 Columna dirección: {args.direccion}")
    print(f"🏥 Instance: {args.instance}")
    print("-" * 60)
    
    success = process_excel(args.excel, args.nombre, args.direccion, args.output)
    
    if success:
        print("\n🎉 ¡Proceso completado exitosamente!")
    else:
        print("\n❌ El proceso falló. Revisa los errores anteriores.")

if __name__ == "__main__":
    main()

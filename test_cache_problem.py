"""
Script para investigar el problema del cache con json
"""
import json
import tempfile
from pathlib import Path

def test_cache_read():
    """Probar la lectura del archivo de cache problemático"""
    # Directorio de cache
    cache_dir = Path(tempfile.gettempdir()) / "cached_slots"

    # Los dos archivos que podrían existir
    cache_file_1 = cache_dir / "slots_629203315.json"  # Correcto
    cache_file_2 = cache_dir / "slots_34629203315.json"  # Problemático del log

    print(f"Cache directory: {cache_dir}")
    print(f"Cache dir exists: {cache_dir.exists()}")

    if cache_dir.exists():
        print("\nArchivos en el directorio de cache:")
        for f in cache_dir.glob("slots_*629203315*.json"):
            print(f"  {f}")

    # Probar lectura del archivo problemático
    if cache_file_2.exists():
        print(f"\nProbando lectura de: {cache_file_2}")
        try:
            with cache_file_2.open('r', encoding='utf-8') as f:
                content = f.read()
                print(f"Tamaño del archivo: {len(content)} caracteres")
                print(f"Primeros 200 caracteres:\n{content[:200]}...")

                # Intentar parsear JSON
                f.seek(0)  # Volver al inicio
                try:
                    data = json.load(f)
                    print("JSON parseado correctamente")
                    print(f"Tipo: {type(data)}")
                    if isinstance(data, dict):
                        print(f"Claves principales: {list(data.keys())[:5]}")
                except json.JSONDecodeError as je:
                    print(f"Error parseando JSON: {je}")

        except Exception as e:
            print(f"Error leyendo archivo: {e}")
    else:
        print(f"\nArchivo {cache_file_2} no existe")

    # Probar el correcto también
    if cache_file_1.exists():
        print(f"\nProbando lectura de: {cache_file_1}")
        try:
            with cache_file_1.open('r', encoding='utf-8') as f:
                data = json.load(f)
                print("JSON parseado correctamente en archivo correcto")
        except Exception as e:
            print(f"Error leyendo archivo correcto: {e}")

if __name__ == "__main__":
    test_cache_read()
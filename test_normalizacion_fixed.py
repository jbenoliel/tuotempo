"""
Script para probar que la normalización funciona correctamente ahora
"""
import re
import sys
import os
sys.path.append(os.getcwd())

# Importar la función desde el módulo
def _norm_phone(phone: str) -> str:
    """Normaliza un número de teléfono eliminando caracteres no numéricos."""
    if not phone:
        return ""
    phone_digits = re.sub(r'\D', '', str(phone))
    # Tomar los últimos 9 dígitos para números españoles
    if len(phone_digits) > 9:
        phone_digits = phone_digits[-9:]
    return phone_digits

def test_phone_normalization():
    """Probar diferentes formatos de teléfono"""
    test_cases = [
        "+34629203315",
        "34629203315",
        " +34 629 203 315 ",
        "629203315",
        "+34-629-203-315"
    ]

    print("=== PRUEBA DE NORMALIZACION ESTANDARIZADA ===")
    for phone in test_cases:
        normalized = _norm_phone(phone)
        cache_file = f"slots_{normalized}.json"
        print(f"Original: '{phone}' -> Normalizado: '{normalized}' -> Cache: '{cache_file}'")

    print("\n=== CASOS ESPECIALES ===")
    # Casos especiales que aparecían en los logs
    special_cases = [
        "34629203315",  # Este era el problemático del log
        "+34629203315"   # Este debería dar el mismo resultado
    ]

    for phone in special_cases:
        normalized = _norm_phone(phone)
        print(f"Especial: '{phone}' -> '{normalized}'")

    # Verificar que ambos dan el mismo resultado
    norm1 = _norm_phone("34629203315")
    norm2 = _norm_phone("+34629203315")
    print(f"\n¿Son iguales 34629203315 y +34629203315? {norm1 == norm2}")
    print(f"norm1: '{norm1}', norm2: '{norm2}'")

if __name__ == "__main__":
    test_phone_normalization()
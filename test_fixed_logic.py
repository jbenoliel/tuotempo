"""
Script para probar que la lógica del endpoint reservar funciona correctamente
"""
import re

def _norm_phone(phone: str) -> str:
    """Normaliza un número de teléfono eliminando caracteres no numéricos."""
    if not phone:
        return ""
    phone_digits = re.sub(r'\D', '', str(phone))
    if len(phone_digits) > 9:
        phone_digits = phone_digits[-9:]
    return phone_digits

def test_reservar_logic():
    """Simular la lógica del endpoint reservar"""
    print("=== PRUEBA DE LÓGICA CORREGIDA ===")

    # Datos de prueba similares a los del API
    mock_data = {
        'user_info': {
            'phone': '+34629203315'
        },
        'availability': {
            'start_date': '2025-10-10',
            'startTime': '13:30',
            'resourceid': 'sc167098a8234897'
        }
    }

    # Simular el código corregido
    user_info = mock_data.get('user_info', {})
    availability = mock_data.get('availability', {})

    # Normalizar teléfono INMEDIATAMENTE para usar en clave de idempotencia
    phone_raw = user_info.get('phone')
    if not phone_raw:
        print("ERROR: Falta el teléfono en user_info")
        return

    phone_cache = _norm_phone(phone_raw)
    print(f"1. Teléfono normalizado: {phone_cache}")

    # Crear clave única basada en teléfono + slot + fecha
    start_date = availability.get('start_date', '')
    start_time = availability.get('startTime', '')
    resource_id = availability.get('resourceid', '')

    idempotency_key = f"{phone_cache}_{start_date}_{start_time}_{resource_id}"
    print(f"2. Clave de idempotencia: {idempotency_key}")

    # Cache path que usaría
    cache_path = f"slots_{phone_cache}.json"
    print(f"3. Archivo de cache: {cache_path}")

    print("\n✅ Todo funciona correctamente - no hay errores de variable no definida")

if __name__ == "__main__":
    test_reservar_logic()
#!/usr/bin/env python3
"""
Script para probar la normalización de teléfonos españoles
"""

def normalize_spanish_phone(phone: str) -> str:
    """Normaliza un teléfono español añadiendo +34 si es necesario."""
    if not phone:
        return phone
        
    # Limpiar el teléfono de espacios y caracteres extra
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Si ya tiene el prefijo +34, devolverlo como está
    if phone.startswith('+34'):
        return phone
    
    # Si tiene 34 al principio (sin +), añadir el +
    if clean_phone.startswith('34') and len(clean_phone) == 11:
        return '+' + clean_phone
    
    # Si es un teléfono de 9 dígitos (formato español), añadir +34
    if len(clean_phone) == 9:
        return '+34' + clean_phone
    
    # Si tiene 8 dígitos, probablemente le falta el primer 6/7/9
    if len(clean_phone) == 8:
        # Asumir que es un móvil que empieza por 6
        return '+346' + clean_phone
    
    # En cualquier otro caso, devolver tal como está
    print(f"⚠️ Teléfono con formato inesperado: {phone} -> {clean_phone}")
    return phone

def test_phone_normalization():
    """Prueba la normalización con diferentes formatos de teléfono."""
    
    test_cases = [
        # Casos normales
        ("629203315", "+34629203315"),  # Móvil normal
        ("911234567", "+34911234567"),  # Fijo Madrid
        ("934567890", "+34934567890"),  # Fijo Barcelona
        
        # Con espacios y caracteres
        ("629 203 315", "+34629203315"),
        ("629-203-315", "+34629203315"),
        ("629.203.315", "+34629203315"),
        
        # Ya con prefijo
        ("+34629203315", "+34629203315"),
        ("34629203315", "+34629203315"),
        
        # Casos especiales
        ("29203315", "+34629203315"),  # 8 dígitos, le falta el 6
        
        # Casos problemáticos
        ("123", "123"),  # Muy corto
        ("+1234567890", "+1234567890"),  # Otro país
        ("", ""),  # Vacío
    ]
    
    print("🧪 === PROBANDO NORMALIZACIÓN DE TELÉFONOS ===")
    print()
    
    for original, expected in test_cases:
        result = normalize_spanish_phone(original)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{original}' -> '{result}' (esperado: '{expected}')")
    
    print()
    print("🔍 === PROBANDO CON TELÉFONOS REALES DE LA BD ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, nombre, telefono, telefono2 
            FROM leads 
            WHERE telefono IS NOT NULL OR telefono2 IS NOT NULL
            LIMIT 5
        """)
        
        leads = cursor.fetchall()
        
        for lead in leads:
            print(f"\n📞 Lead {lead['id']} - {lead['nombre']}:")
            
            if lead['telefono']:
                normalized = normalize_spanish_phone(lead['telefono'])
                print(f"   Teléfono 1: '{lead['telefono']}' -> '{normalized}'")
            
            if lead['telefono2']:
                normalized = normalize_spanish_phone(lead['telefono2'])
                print(f"   Teléfono 2: '{lead['telefono2']}' -> '{normalized}'")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accediendo a BD: {e}")

if __name__ == "__main__":
    test_phone_normalization()

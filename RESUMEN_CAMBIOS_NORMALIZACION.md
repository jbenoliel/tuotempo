# Resumen de Cambios: Normalización de Teléfonos

## Problema Identificado
En los logs se detectó un error "local variable 'json' referenced before assignment" y archivos de cache con nombres inconsistentes:
- Se encontró: `slots_34629203315.json` (incorrecto)
- Debería ser: `slots_629203315.json` (correcto)

## Causa Raíz
Había **tres normalizaciones diferentes** de teléfonos en el código:

1. **obtener_slots**: `_norm_phone(phone)` → `phone_norm`
2. **debug_cache**: `phone.replace('+', '').replace(' ', '')` → `phone_cache`
3. **reservar**: Doble normalización inconsistente

## Cambios Realizados

### 1. Estandarización en `/api/reservar`
```python
# ANTES: Múltiples normalizaciones inconsistentes
phone = user_info.get('phone', '').replace(' ', '').replace('+', '')  # Simple
phone_normalized = _norm_phone(phone_cache)  # Función estándar
if len(phone_normalized) > 9:
    phone_normalized = phone_normalized[-9:]

# DESPUÉS: Una sola normalización estándar
phone_raw = user_info.get('phone')
phone_cache = _norm_phone(phone_raw)  # Inmediata y consistente
```

### 2. Estandarización en `/api/debug/cache`
```python
# ANTES: Normalización manual
phone_cache = phone.replace('+', '').replace(' ', '')
if len(phone_cache) > 9:
    phone_cache = phone_cache[-9:]

# DESPUÉS: Función estándar
phone_cache = _norm_phone(phone)
```

### 3. Corrección de clave de idempotencia
```python
# ANTES: Usaba teléfono sin normalizar
idempotency_key = f"{phone}_{start_date}_{start_time}_{resource_id}"

# DESPUÉS: Usa teléfono normalizado
idempotency_key = f"{phone_cache}_{start_date}_{start_time}_{resource_id}"
```

### 4. Simplificación de cache lookup
```python
# ANTES: Doble normalización
phone_normalized = _norm_phone(phone_cache)
if len(phone_normalized) > 9:
    phone_normalized = phone_normalized[-9:]
cache_path = SLOTS_CACHE_DIR / f"slots_{phone_normalized}.json"

# DESPUÉS: Teléfono ya normalizado
cache_path = SLOTS_CACHE_DIR / f"slots_{phone_cache}.json"
```

## Resultado Final
✅ **Todos los teléfonos** ahora se normalizan consistentemente a: `629203315`
✅ **Todos los archivos de cache** tendrán el nombre: `slots_629203315.json`
✅ **Todas las claves de idempotencia** usarán el mismo formato
✅ **Eliminadas las inconsistencias** que causaban el error de `json`

## Función de Normalización Estándar
```python
def _norm_phone(phone: str) -> str:
    """Normaliza un número de teléfono eliminando caracteres no numéricos."""
    if not phone:
        return ""
    phone_digits = re.sub(r'\D', '', str(phone))
    # Tomar los últimos 9 dígitos para números españoles
    if len(phone_digits) > 9:
        phone_digits = phone_digits[-9:]
    return phone_digits
```

## Casos de Prueba
Todos estos inputs ahora dan el mismo resultado:
- `"+34629203315"` → `"629203315"`
- `"34629203315"` → `"629203315"`
- `" +34 629 203 315 "` → `"629203315"`
- `"629203315"` → `"629203315"`
- `"+34-629-203-315"` → `"629203315"`
# Flujo Completo de APIs de Reservas en Railway

## 🔍 Problema Identificado

El `activityId` por defecto **SÍ está implementado** en `api_tuotempo.py`, pero hay **DOS APIs diferentes** para reservas:

1. **`api_tuotempo.py`** - API principal con lógica de caché ✅
2. **`reservation_api.py`** - Wrapper simplificado ❌ (sin activityId por defecto)

## 📋 Flujo Actual del Sistema

### 1. **Obtener Slots** (`/api/slots`)
```
Cliente → GET /api/slots?phone=XXX&centro_id=YYY
       ↓
   TuoTempo API (obtener disponibilidad)
       ↓
   Guardar en caché: /tmp/cached_slots/slots_XXX.json
       ↓
   Devolver slots al cliente
```

### 2. **Reservar Slot** (`/api/reservar`)
```
Cliente → POST /api/reservar
       ↓
   ¿Faltan campos críticos? (endTime, resourceid, activityid)
       ↓ SÍ
   Buscar en caché por teléfono + fecha + hora
       ↓
   Completar datos faltantes desde caché
       ↓
   ¿Sigue faltando activityid?
       ↓ SÍ
   Asignar activityId por defecto: 'sc159232371eb9c1'
       ↓
   Llamar a TuoTempo API para confirmar reserva
```

## 🎯 APIs Disponibles

### **API Principal** (`api_tuotempo.py`) - ✅ CORRECTO
- **URL**: `https://tuotempo-apis-production.up.railway.app/api/reservar`
- **Lógica de activityId**: ✅ Implementada
- **Caché de slots**: ✅ Implementado
- **Campos mínimos requeridos**:
  ```json
  {
    "user_info": {
      "fname": "Juan",
      "lname": "Pérez", 
      "phone": "+34612345678"
    },
    "availability": {
      "start_date": "2025-08-15",
      "startTime": "10:00"
      // endTime, resourceid, activityid se completan desde caché
    }
  }
  ```

### **API Wrapper** (`reservation_api.py`) - ❌ PROBLEMA
- **URL**: `https://tuotempo-apis-production.up.railway.app/reserve`
- **Lógica de activityId**: ❌ NO implementada (recién añadida)
- **Caché de slots**: ❌ No usa caché
- **Campos requeridos**:
  ```json
  {
    "userid": "user123",
    "phone": "+34612345678",
    "slot": {
      "start_date": "2025-08-15",
      "startTime": "10:00",
      "endTime": "10:30",
      "resourceid": "resource123",
      "areaid": "area123"
      // activityid es opcional (se asigna por defecto)
    }
  }
  ```

## 🔧 Solución Implementada

He añadido la lógica de `activityId` por defecto al wrapper `reservation_api.py`:

```python
# Si activityid no está presente, usar valor por defecto
if 'activityid' not in slot_data or not slot_data['activityid']:
    default_activity_id = os.getenv('TUOTEMPO_ACTIVITY_ID', 'sc159232371eb9c1')
    slot_data['activityid'] = default_activity_id
    app.logger.info(f"activityId no presente. Usando valor por defecto: {default_activity_id}")
```

## 📊 Comparación de APIs

| Característica | `api_tuotempo.py` | `reservation_api.py` |
|---------------|-------------------|---------------------|
| **URL** | `/api/reservar` | `/reserve` |
| **Caché de slots** | ✅ Sí | ❌ No |
| **activityId por defecto** | ✅ Sí | ✅ Sí (recién añadido) |
| **Campos mínimos** | 3 campos | 5+ campos |
| **Completado automático** | ✅ Desde caché | ❌ No |
| **Uso recomendado** | Frontend principal | Integraciones externas |

## 🚀 Recomendación

### **Para el flujo principal** (Frontend → Backend):
1. **Usar `/api/slots`** para obtener disponibilidad
2. **Usar `/api/reservar`** para confirmar reserva
3. El sistema automáticamente:
   - Completa campos faltantes desde caché
   - Asigna `activityId` por defecto si falta

### **Para integraciones externas**:
1. **Usar `/reserve`** con todos los datos del slot
2. El `activityId` se asigna automáticamente si no se proporciona

## 🔍 Debugging

### Para verificar si el activityId se asigna correctamente:

```bash
# Verificar logs de la API
grep "activityId.*por defecto" logs/

# Test manual del endpoint principal
curl -X POST https://tuotempo-apis-production.up.railway.app/api/reservar \
  -H "Content-Type: application/json" \
  -d '{
    "user_info": {"fname":"Test","lname":"User","phone":"123456789"},
    "availability": {"start_date":"2025-08-01","startTime":"10:00"}
  }'

# Test manual del wrapper
curl -X POST https://tuotempo-apis-production.up.railway.app/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "userid": "test123",
    "phone": "123456789",
    "slot": {
      "start_date": "2025-08-01",
      "startTime": "10:00",
      "endTime": "10:30",
      "resourceid": "resource123",
      "areaid": "area123"
    }
  }'
```

## ✅ Estado Actual

- ✅ **API principal**: activityId por defecto funcionando
- ✅ **API wrapper**: activityId por defecto añadido
- ✅ **Caché de slots**: funcionando correctamente
- ✅ **Completado automático**: funcionando

**El problema del activityId por defecto debería estar resuelto en ambas APIs.**

# API /api/reservar - Parámetros Indispensables

## Resumen Ejecutivo

**¿Es necesario el activityId?** **SÍ**, es uno de los 3 campos críticos obligatorios.

**Parámetros indispensables mínimos:**
1. `user_info` (información del usuario)
2. `availability` (información de la cita) 
3. `phone` (dentro de user_info)

## Estructura Completa de la API

### URL
- **Endpoint**: `/api/reservar`
- **Método**: `POST`
- **Content-Type**: `application/json`

### Parámetros del Cuerpo (JSON)

#### 1. **user_info** (OBLIGATORIO)
Información del usuario que hará la reserva:

```json
{
  "user_info": {
    "fname": "Juan",           // OBLIGATORIO - Nombre
    "lname": "Pérez",          // OBLIGATORIO - Apellidos  
    "phone": "+34612345678",   // OBLIGATORIO - Teléfono
    "birthday": "1990-01-15"   // OPCIONAL - Fecha nacimiento (YYYY-MM-DD)
  }
}
```

**Campos obligatorios en user_info:**
- `fname`: Nombre del usuario
- `lname`: Apellidos del usuario  
- `phone`: Teléfono del usuario (usado también como cache key)

#### 2. **availability** (OBLIGATORIO)
Información del slot de cita a reservar:

```json
{
  "availability": {
    "start_date": "2025-08-15",           // OBLIGATORIO - Fecha (YYYY-MM-DD)
    "startTime": "10:00",                 // OBLIGATORIO - Hora inicio (HH:MM)
    "endTime": "10:30",                   // OBLIGATORIO - Hora fin (HH:MM)
    "resourceid": "resource_123",         // OBLIGATORIO - ID del recurso/doctor
    "activityid": "sc159232371eb9c1"      // OBLIGATORIO - ID de la actividad
  }
}
```

**Campos críticos obligatorios en availability:**
- `endTime`: Hora de finalización
- `resourceid`: ID del recurso (doctor/sala)
- `activityid`: ID de la actividad (tipo de cita)

**Campos adicionales obligatorios:**
- `start_date`: Fecha de la cita
- `startTime`: Hora de inicio

#### 3. **env** (OPCIONAL)
Entorno de ejecución:
- `"PRO"` (por defecto): Producción
- `"PRE"`: Pre-producción

## Campos Críticos y Validación

### Validación Automática
La API valida que existan estos 3 campos críticos:
```python
critical_keys = {'endTime', 'resourceid', 'activityid'}
```

### Comportamiento del activityId por Defecto

**✅ FUNCIONALIDAD IMPLEMENTADA:**
Si `activityid` no está presente o está vacío, la API automáticamente asigna:

```python
# Valor por defecto del activityId
default_activity_id = os.getenv('TUOTEMPO_ACTIVITY_ID', 'sc159232371eb9c1')
```

**Orden de prioridad para activityId:**
1. `availability.activityid` (si existe y no está vacío)
2. `availability.activityId` (camelCase, se convierte a snake_case)
3. `availability.activity_id` (snake_case alternativo)
4. Variable de entorno `TUOTEMPO_ACTIVITY_ID`
5. Valor hardcoded: `'sc159232371eb9c1'`

## Ejemplo Completo de Uso

### Ejemplo Mínimo (con activityId)
```json
POST /api/reservar
Content-Type: application/json

{
  "user_info": {
    "fname": "Juan",
    "lname": "Pérez", 
    "phone": "+34612345678"
  },
  "availability": {
    "start_date": "2025-08-15",
    "startTime": "10:00",
    "endTime": "10:30", 
    "resourceid": "resource_123",
    "activityid": "sc159232371eb9c1"
  }
}
```

### Ejemplo Sin activityId (usa valor por defecto)
```json
POST /api/reservar
Content-Type: application/json

{
  "user_info": {
    "fname": "Juan",
    "lname": "Pérez",
    "phone": "+34612345678"
  },
  "availability": {
    "start_date": "2025-08-15", 
    "startTime": "10:00",
    "endTime": "10:30",
    "resourceid": "resource_123"
    // activityid se asignará automáticamente
  }
}
```

### Ejemplo Completo con Todos los Campos
```json
POST /api/reservar
Content-Type: application/json

{
  "env": "PRO",
  "user_info": {
    "fname": "Juan",
    "lname": "Pérez González",
    "phone": "+34612345678",
    "birthday": "1990-01-15"
  },
  "availability": {
    "start_date": "2025-08-15",
    "startTime": "10:00", 
    "endTime": "10:30",
    "resourceid": "resource_123",
    "activityid": "sc159232371eb9c1"
  }
}
```

## Respuestas de la API

### Respuesta Exitosa (200)
```json
{
  "result": "OK",
  "msg": "Cita confirmada correctamente",
  "appointment_id": "12345",
  "details": {
    // Detalles adicionales de TuoTempo
  }
}
```

### Errores Comunes

#### 400 - Campos Faltantes
```json
{
  "error": "Faltan campos clave: user_info, availability o phone"
}
```

#### 400 - Campos Críticos Faltantes  
```json
{
  "error": "Faltan campos críticos para la reserva: ['endTime', 'resourceid']. No se pudieron completar desde la caché."
}
```

#### 502 - Error de TuoTempo
```json
{
  "error": "No se pudo confirmar la cita",
  "details": {
    "result": "ERROR",
    "msg": "Mensaje de error de TuoTempo"
  }
}
```

## Normalización Automática de Campos

La API normaliza automáticamente estos formatos:

### Formatos de activityId Soportados:
- `activityid` ✅ (formato preferido)
- `activityId` → se convierte a `activityid`
- `activity_id` → se convierte a `activityid`

### Formatos de resourceId Soportados:
- `resourceid` ✅ (formato preferido)  
- `resourceId` → se convierte a `resourceid`
- `resource_id` → se convierte a `resourceid`

## Caché de Slots

Si faltan campos críticos, la API intenta completarlos desde el caché de slots basado en:
- Teléfono del usuario
- Fecha de la cita (`start_date`)
- Hora de inicio (`startTime`)

## Resumen de Campos Obligatorios

### ✅ OBLIGATORIOS SIEMPRE:
1. `user_info.fname` - Nombre
2. `user_info.lname` - Apellidos
3. `user_info.phone` - Teléfono
4. `availability.start_date` - Fecha
5. `availability.startTime` - Hora inicio
6. `availability.endTime` - Hora fin
7. `availability.resourceid` - ID recurso
8. `availability.activityid` - ID actividad (o se asigna automáticamente)

### ✅ OPCIONALES:
- `user_info.birthday` - Fecha de nacimiento
- `env` - Entorno (PRO por defecto)

**Total: 7 campos obligatorios mínimos + 1 que se asigna automáticamente si falta**

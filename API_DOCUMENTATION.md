# Documentación de la API de TuoTempo

Esta documentación describe los endpoints disponibles en la API de TuoTempo para la gestión de resultados de llamadas a contactos.

## Base URL

- **Entorno local**: `http://localhost:5000`
- **Entorno de producción**: `https://tuotempo-production.up.railway.app`

## Autenticación

Actualmente, la API no requiere autenticación específica. Sin embargo, se recomienda implementar un sistema de autenticación en futuras versiones para mayor seguridad.

## Endpoints disponibles

### 1. Estado de la API

Verifica que la API esté funcionando correctamente.

- **URL**: `/api/status`
- **Método**: `GET`
- **Parámetros**: Ninguno

**Respuesta exitosa**:
```json
{
  "service": "API Resultado Llamada",
  "status": "online",
  "timestamp": "2025-06-30 12:30:00"
}
```

**Ejemplo de uso**:
```python
import requests

response = requests.get("http://localhost:5000/api/status")
print(response.json())
```

### 2. Obtener resultados de llamadas

Obtiene la lista de contactos filtrados opcionalmente por resultado de llamada.

- **URL**: `/api/obtener_resultados`
- **Método**: `GET`
- **Parámetros**:
  - `resultado` (opcional): Filtrar por resultado de llamada (ej: "no interesado", "interesado", "no contesta")

**Respuesta exitosa**:
```json
{
  "contactos": [
    {
      "apellidos": "PEREIRA DUARTE",
      "cita": null,
      "conPack": 0,
      "id": 1,
      "nombre": "ADAM",
      "resultado_llamada": null,
      "telefono": "672663119",
      "telefono2": "",
      "codigo_postal": "28041",
      "provincia": "MADRID"
    },
    // ... más contactos
  ],
  "count": 25,
  "success": true
}
```

**Ejemplo de uso**:
```python
import requests

# Obtener todos los contactos
response = requests.get("http://localhost:5000/api/obtener_resultados")
print(f"Total de contactos: {response.json()['count']}")

# Filtrar por resultado de llamada
response = requests.get("http://localhost:5000/api/obtener_resultados?resultado=no%20interesado")
print(f"Contactos no interesados: {response.json()['count']}")
```

### 3. Actualizar resultado de llamada

Actualiza el resultado de una llamada para un contacto específico identificado por su número de teléfono.

- **URL**: `/api/actualizar_resultado`
- **Método**: `POST`
- **Cuerpo de la solicitud** (JSON):
  - `telefono` (requerido): Número de teléfono del contacto
  - `resultado_llamada` (opcional): Resultado personalizado de la llamada
  - `interesado` (opcional, booleano): Marca el contacto como interesado
  - `no_interesado` (opcional, booleano): Marca el contacto como no interesado
  - `no_contesta` (opcional, booleano): Marca el contacto como no contesta
  - `nuevaCita` (opcional, string): Fecha de la cita en formato DD/MM/YYYY
  - `horaCita` (opcional, string): Hora de la cita en formato HH:MM:SS o HH:MM
  - `conPack` (opcional, booleano): Marca si el contacto tiene pack
  - `horaRellamada` (opcional, string): Fecha y hora para volver a llamar en formato ISO

**Respuesta exitosa**:
```json
{
  "message": "Resultado de llamada actualizado para el teléfono 672663119",
  "resultado": "no interesado",
  "rows_affected": 1,
  "success": true
}
```

**Respuesta de error**:
```json
{
  "error": "No se encontró ningún contacto con el teléfono proporcionado",
  "success": false
}
```

**Ejemplo de uso**:
```python
import requests

# Marcar como no interesado
data = {
    "telefono": "672663119",
    "no_interesado": True
}
response = requests.post("http://localhost:5000/api/actualizar_resultado", json=data)
print(response.json())

# Marcar como interesado con cita
data = {
    "telefono": "614421251",
    "interesado": True,
    "cita": True
}
response = requests.post("http://localhost:5000/api/actualizar_resultado", json=data)
print(response.json())

# Establecer un resultado personalizado
data = {
    "telefono": "627614713",
    "resultado_llamada": "Llamar más tarde"
}
response = requests.post("http://localhost:5000/api/actualizar_resultado", json=data)
print(response.json())
```

## Códigos de estado HTTP

- `200 OK`: La solicitud se ha procesado correctamente
- `400 Bad Request`: Parámetros incorrectos o faltantes
- `404 Not Found`: Recurso no encontrado
- `500 Internal Server Error`: Error interno del servidor

## Manejo de errores

Todas las respuestas de error incluyen un campo `success` con valor `false` y un campo `error` que describe el problema.

```json
{
  "error": "Descripción del error",
  "success": false
}
```

## Ejemplos de integración

### Ejemplo en Python

```python
import requests

BASE_URL = "http://localhost:5000"

def verificar_api():
    """Verifica que la API esté funcionando"""
    response = requests.get(f"{BASE_URL}/api/status")
    return response.json()["status"] == "online"

def obtener_contactos(resultado=None):
    """Obtiene la lista de contactos, opcionalmente filtrados por resultado"""
    params = {}
    if resultado:
        params["resultado"] = resultado
    
    response = requests.get(f"{BASE_URL}/api/obtener_resultados", params=params)
    return response.json()

def actualizar_resultado(telefono, **kwargs):
    """Actualiza el resultado de llamada para un contacto"""
    data = {"telefono": telefono, **kwargs}
    response = requests.post(f"{BASE_URL}/api/actualizar_resultado", json=data)
    return response.json()

# Ejemplo de uso
if __name__ == "__main__":
    if verificar_api():
        print("API en línea")
        
        # Obtener todos los contactos
        contactos = obtener_contactos()
        print(f"Total de contactos: {contactos['count']}")
        
        if contactos["count"] > 0:
            # Tomar el primer contacto como ejemplo
            telefono = contactos["contactos"][0]["telefono"]
            
            # Actualizar resultado
            resultado = actualizar_resultado(telefono, no_interesado=True)
            print(f"Resultado actualizado: {resultado['success']}")
            
            # Verificar actualización
            contactos_actualizados = obtener_contactos("no interesado")
            print(f"Contactos no interesados: {contactos_actualizados['count']}")
```

### Ejemplo en JavaScript

```javascript
const BASE_URL = "http://localhost:5000";

// Verificar estado de la API
async function verificarAPI() {
  const response = await fetch(`${BASE_URL}/api/status`);
  const data = await response.json();
  return data.status === "online";
}

// Obtener contactos
async function obtenerContactos(resultado = null) {
  let url = `${BASE_URL}/api/obtener_resultados`;
  if (resultado) {
    url += `?resultado=${encodeURIComponent(resultado)}`;
  }
  
  const response = await fetch(url);
  return await response.json();
}

// Actualizar resultado
async function actualizarResultado(telefono, opciones = {}) {
  const data = { telefono, ...opciones };
  
  const response = await fetch(`${BASE_URL}/api/actualizar_resultado`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });
  
  return await response.json();
}

// Ejemplo de uso
async function ejemploUso() {
  if (await verificarAPI()) {
    console.log("API en línea");
    
    // Obtener todos los contactos
    const contactos = await obtenerContactos();
    console.log(`Total de contactos: ${contactos.count}`);
    
    if (contactos.count > 0) {
      // Tomar el primer contacto como ejemplo
      const telefono = contactos.contactos[0].telefono;
      
      // Actualizar resultado
      const resultado = await actualizarResultado(telefono, { no_interesado: true });
      console.log(`Resultado actualizado: ${resultado.success}`);
      
      // Verificar actualización
      const contactosActualizados = await obtenerContactos("no interesado");
      console.log(`Contactos no interesados: ${contactosActualizados.count}`);
    }
  }
}

ejemploUso();
```

## Notas adicionales

- Todos los endpoints devuelven respuestas en formato JSON
- Se recomienda implementar un sistema de autenticación para proteger los endpoints en un entorno de producción
- Los números de teléfono deben proporcionarse sin espacios ni caracteres especiales
- Para cualquier problema o sugerencia, contactar al administrador del sistema

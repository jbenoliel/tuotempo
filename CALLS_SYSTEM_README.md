# 📞 Sistema de Llamadas Automáticas con Pearl AI

Sistema completo de gestión de llamadas automáticas integrado con Pearl AI para el proyecto TuoTempo.

## 🚀 Características Principales

### ✅ **Gestión Completa de Llamadas**
- **Interfaz visual** para control de llamadas (START/STOP)
- **Selección inteligente** de leads con filtros avanzados
- **Monitoreo en tiempo real** de estadísticas y progreso
- **Sistema de prioridades** para optimizar el orden de llamadas

### ✅ **Integración con Pearl AI**
- **API completa** para realizar llamadas automáticas
- **Gestión de campañas** outbound
- **Validación automática** de números de teléfono
- **Manejo de errores** y reintentos inteligentes

### ✅ **Base de Datos Avanzada**
- **10 nuevos campos** para gestión de llamadas
- **Estados detallados** (seleccionado, llamando, completado, error, etc.)
- **Historial completo** de intentos y respuestas
- **Sistema de callbacks** para actualizaciones en tiempo real

### ✅ **Interfaz Moderna Mejorada**
- **Dashboard reactivo** con Bootstrap 5 y diseño corporativo
- **Botones de selección reorganizados** con colores distintivos y mejor espaciado
- **Selección inteligente** que procesa TODOS los leads filtrados (no solo página actual)
- **Procesamiento por lotes** para selecciones masivas (>100 leads)
- **Filtros dinámicos** por Estado 1, Estado 2, Status de llamada, prioridad y selección
- **Paginación inteligente** para grandes volúmenes
- **Contadores en tiempo real** de leads totales y seleccionados
- **Notificaciones toast** para feedback inmediato

## 📋 Instalación y Configuración

### **1. Ejecutar Migración de Base de Datos**

```bash
cd /ruta/a/tuotempo
python db_migration_add_call_fields.py
```

### **2. Configurar Variables de Entorno**

Copia `.env.example` a `.env` y configura:

```bash
# Pearl AI - Credenciales
PEARL_ACCOUNT_ID=tu_account_id_aqui
PEARL_SECRET_KEY=tu_secret_key_aqui
PEARL_API_URL=https://api.nlpearl.ai/v1
PEARL_OUTBOUND_ID=tu_outbound_id_por_defecto
```

### **3. Verificar Instalación**

```bash
# Probar conexión con Pearl AI
python pearl_caller.py

# Probar gestor de llamadas
python call_manager.py
```

## 🎯 Uso del Sistema

### **Acceso al Gestor**
1. Inicia sesión en el dashboard de TuoTempo con credenciales: **admin/admin**
2. Accede a la URL: `http://localhost:8080/calls-manager`

### **Workflow Típico**
1. **Filtrar leads** por Estado 1, Estado 2, Status de llamada, prioridad o selección
2. **Seleccionar leads** usando las nuevas opciones mejoradas:
   - 🟢 **"Seleccionar Todo"** - Selecciona TODOS los leads que coincidan con filtros activos
   - 🟡 **"Deseleccionar Todo"** - Deselecciona todos los leads
   - 🔵 **"Seleccionar por Estado"** - Dropdown con opciones por estados específicos
   - 🔘 **Checkboxes individuales** - Selección manual lead por lead
3. **Gestionar leads**:
   - 🔧 **"Gestión Manual"** - Marca leads para gestión manual vs automática
   - 🔄 **"Reiniciar Estados"** - Limpia errores técnicos y reinicia contadores (mantiene selecciones)
4. **Iniciar llamadas** con el botón START
5. **Monitorear progreso** en tiempo real
6. **Detener cuando sea necesario** con el botón STOP

### **🎨 Controles de Interfaz Mejorados**

#### **Fila 1: Selección Principal**
- **🟢 Seleccionar Todo** - Selecciona TODOS los leads que coincidan con los filtros activos (no solo la página actual)
- **🟡 Deseleccionar Todo** - Deselecciona todos los leads seleccionados

#### **Fila 2: Acciones Avanzadas**
- **🔵 Seleccionar por Estado** - Dropdown con opciones:
  - Estados principales: "Volver a llamar", "No Interesado", "Éxito", "Cita Agendada"
  - Estados de llamada: "Sin llamar", "Completadas", "Con Error"
- **🔘 Gestión Manual** - Dropdown para:
  - Marcar leads como gestión manual
  - Marcar leads como gestión automática  
- **🔄 Reiniciar Estados** - Limpia errores técnicos y reinicia contadores (mantiene las selecciones)

#### **💡 Funcionalidades Destacadas**
- **Procesamiento por lotes**: Para selecciones >100 leads, procesa en grupos para evitar timeouts
- **Confirmaciones inteligentes**: Pide confirmación para selecciones >50 leads
- **Indicadores de progreso**: Muestra progreso en operaciones masivas
- **Tooltips informativos**: Información detallada sobre cada botón

### **Estados de Llamada**
- 🔘 **no_selected**: Lead no seleccionado para llamadas
- 🟦 **selected**: Lead marcado para llamar
- 🟡 **calling**: Llamada en progreso
- 🟢 **completed**: Llamada completada exitosamente
- 🔴 **error**: Error en la llamada
- 🟠 **busy**: Línea ocupada
- 🟣 **no_answer**: Sin respuesta

## 📊 API Endpoints

### **Estado del Sistema**
```http
GET /api/calls/status
```
Obtiene el estado completo del sistema de llamadas, estadísticas de leads y conexión con Pearl AI.

### **Control de Llamadas**
```http
POST /api/calls/start
POST /api/calls/stop
```
- **POST /start**: Inicia el sistema de llamadas automáticas
  - Body (opcional): `{"max_concurrent": 3, "selected_leads": [1,2,3], "override_phone": "+34600000000"}`
- **POST /stop**: Detiene todas las llamadas activas

### **Gestión de Leads**
```http
GET /api/calls/leads?city=Madrid&status=selected&limit=50&offset=0&priority=1
POST /api/calls/leads/select
POST /api/calls/leads/manual-management
POST /api/calls/leads/reset
```
- **GET /leads**: Obtiene leads con filtros avanzados (ciudad, estado, prioridad, paginación)
- **POST /select**: Selecciona leads para llamadas
  - Body: `{"lead_ids": [1,2,3], "action": "select|deselect", "filters": {...}}`
- **POST /manual-management**: Marca leads para gestión manual/automática
  - Body: `{"lead_ids": [1,2,3], "manual": true|false}`
- **POST /reset**: Reinicia estados de llamadas de leads seleccionados

### **Configuración del Sistema**
```http
GET /api/calls/configuration
POST /api/calls/configuration
```
- **GET /configuration**: Obtiene la configuración actual del sistema
- **POST /configuration**: Actualiza la configuración
  - Body: `{"maxConcurrentCalls": 5, "retryAttempts": 3, "retryDelay": 300, "overridePhone": null}`

### **Pearl AI**
```http
GET /api/calls/pearl/campaigns
GET /api/calls/test/connection
GET /api/calls/test-connection
```
- **GET /pearl/campaigns**: Lista todas las campañas disponibles en Pearl AI
- **GET /test/connection**: Prueba detallada de conexión con Pearl AI
- **GET /test-connection**: Prueba simple de conexión con Pearl AI

### **Historial y Monitoreo de Llamadas**
```http
GET /api/calls/history
GET /api/calls/history/stats
GET /api/calls/schedule
```
- **GET /history**: Obtiene historial detallado de llamadas desde pearl_calls
  - Parámetros: `limit`, `offset`, `lead_id`, `status`, `from_date`, `to_date`
  - Respuesta: Historial completo con información de leads, duración, costos, transcripciones
- **GET /history/stats**: Estadísticas resumidas del historial de llamadas
  - Respuesta: Estadísticas generales, por día, y por resultado
- **GET /schedule**: Obtiene llamadas programadas desde call_schedule
  - Parámetros: `limit`, `offset`, `status`, `lead_id`, `from_date`, `to_date`
  - Respuesta: Llamadas programadas con información de leads y estado

### **Administración**
```http
POST /api/calls/admin/cleanup-selected
```
- **POST /admin/cleanup-selected**: Limpia leads seleccionados huérfanos (uso administrativo)

### **API de Resultado de Llamadas** ⭐
```http
GET /api/status
POST /api/actualizar_resultado
GET /api/leads_reserva_automatica
GET /api/obtener_resultados
POST /api/marcar_reserva_automatica
```

- **GET /api/status**: Estado de la API general del sistema
- **POST /api/actualizar_resultado**: Actualiza el resultado de una llamada específica
  - Body: `{"telefono": "699106495", "volverALlamar": true, "razonvueltaallamar": "Cliente ocupado", "codigoVolverLlamar": "ocupado", "buzon": false}`
- **GET /api/leads_reserva_automatica**: Obtiene leads marcados para reserva automática
- **GET /api/obtener_resultados**: Obtiene contactos filtrados por resultado de llamada
  - Query params: `?resultado=exitoso&limit=50&offset=0`
- **POST /api/marcar_reserva_automatica**: Marca/desmarca leads para reserva automática
  - Body: `{"telefono": "699106495", "reserva_automatica": true}`

> **IMPORTANTE**: Esta API es utilizada por sistemas externos (como Pearl AI) para actualizar los resultados de las llamadas realizadas automáticamente.

### **Ejemplos de Respuesta**

**GET /api/calls/status** - Respuesta:
```json
{
  "success": true,
  "timestamp": "2025-09-03T16:30:45.123456",
  "system_status": {
    "call_manager": {
      "is_running": false,
      "active_calls": 0,
      "total_calls_made": 0,
      "max_concurrent_calls": 3
    },
    "pearl_connection": true,
    "default_outbound_id": "686294f10d5921f7a531653a"
  },
  "leads_summary": {
    "total_leads": 848,
    "selected_for_calling": 0,
    "status_breakdown": [
      {"call_status": "no_selected", "count": 848, "selected_count": 0}
    ]
  }
}
```

**GET /api/calls/leads** - Respuesta:
```json
{
  "leads": [
    {
      "id": 645,
      "telefono": "699106495",
      "call_status": "no_selected",
      "call_priority": 3,
      "selected_for_calling": false,
      "nombre": "Juan",
      "apellidos": "Pérez",
      "ciudad": "Madrid"
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 170,
    "total_count": 848,
    "per_page": 5
  },
  "filters_applied": {
    "city": null,
    "status": null,
    "priority": null,
    "selected_only": false
  }
}
```

**POST /api/calls/start** - Respuesta exitosa:
```json
{
  "success": true,
  "message": "Sistema de llamadas iniciado correctamente",
  "leads_queued": 15,
  "configuration": {
    "max_concurrent_calls": 3,
    "override_phone": null
  }
}
```

**GET /api/calls/configuration** - Respuesta:
```json
{
  "configuration": {
    "maxConcurrentCalls": 3,
    "retryAttempts": 3,
    "retryDelay": 300,
    "overridePhone": null
  }
}
```

**GET /api/status** - Respuesta:
```json
{
  "service": "API Centros TuoTempo",
  "status": "online",
  "timestamp": "2025-09-03 18:17:06"
}
```

**POST /api/actualizar_resultado** - Body de ejemplo:
```json
{
  "telefono": "699106495",
  "volverALlamar": true,
  "razonvueltaallamar": "Cliente ocupado, solicita llamar mañana",
  "codigoVolverLlamar": "ocupado",
  "buzon": false,
  "codigoNoInteres": null,
  "resultado": "pendiente_contacto",
  "observaciones": "Cliente interesado pero no disponible ahora"
}
```

**GET /api/leads_reserva_automatica** - Respuesta:
```json
{
  "success": true,
  "count": 2,
  "leads": [
    {
      "id": 123,
      "telefono": "699106495",
      "nombre": "Juan",
      "apellidos": "Pérez",
      "reserva_automatica": true,
      "fecha_marcado": "2025-09-03T16:30:00"
    }
  ]
}
```

**GET /api/obtener_resultados** - Respuesta:
```json
{
  "contactos": [
    {
      "id": 645,
      "nombre": "CARLOS",
      "apellidos": "PEÑA PULIDO",
      "telefono": "699106495",
      "resultado": "exitoso",
      "fecha_llamada": "2025-09-03T15:30:00",
      "observaciones": "Cliente interesado en el producto"
    }
  ],
  "total_count": 150,
  "filtered_count": 25
}
```

**GET /api/calls/history** - Respuesta:
```json
{
  "calls": [
    {
      "id": 1,
      "call_id": "call_67890abcd",
      "phone_number": "600111111",
      "lead_id": 5,
      "nombre": "Juan",
      "apellidos": "Pérez",
      "outbound_id": "686294f10d5921f7a531653a",
      "call_time": "2025-09-08T09:40:00",
      "duration": 45,
      "status": "completed",
      "outcome": "no_answer",
      "summary": "Cliente no respondió la llamada",
      "cost": 0.15,
      "recording_url": "https://...",
      "created_at": "2025-09-08T09:40:04"
    }
  ],
  "pagination": {
    "total": 25,
    "limit": 50,
    "offset": 0,
    "count": 25
  }
}
```

**GET /api/calls/schedule** - Respuesta:
```json
{
  "scheduled_calls": [
    {
      "id": 5,
      "lead_id": 3,
      "nombre": "TestUser1",
      "apellidos": "Apellido1",
      "telefono": "600111111",
      "ciudad": "TestCity1",
      "scheduled_at": "2025-09-08T10:00:00",
      "attempt_number": 2,
      "status": "pending",
      "last_outcome": "invalid_phone",
      "call_attempts_count": 2,
      "lead_status": "open",
      "closure_reason": null
    }
  ],
  "pagination": {
    "total": 5,
    "limit": 50,
    "offset": 0,
    "count": 5
  },
  "status_breakdown": [
    {"status": "pending", "count": 1},
    {"status": "cancelled", "count": 4}
  ]
}
```

**GET /api/calls/history/stats** - Respuesta:
```json
{
  "general": {
    "total_calls": 127,
    "unique_leads": 85,
    "avg_duration": 42.5,
    "total_cost": 19.05,
    "completed_calls": 98,
    "failed_calls": 29,
    "answered_calls": 67,
    "no_answer_calls": 60
  },
  "daily": [
    {
      "call_date": "2025-09-08",
      "calls_count": 15,
      "avg_duration": 38.2
    }
  ],
  "outcomes": [
    {"outcome": "no_answer", "count": 60},
    {"outcome": "answered", "count": 67}
  ]
}
```

### **Códigos de Estado HTTP**

| Código | Descripción | Cuándo se usa |
|--------|-------------|---------------|
| `200` | OK | Operación exitosa |
| `400` | Bad Request | Datos de entrada inválidos o sistema ya en ejecución |
| `404` | Not Found | Recurso no encontrado |
| `405` | Method Not Allowed | Método HTTP incorrecto |
| `500` | Internal Server Error | Error interno del servidor |
| `502` | Bad Gateway | Error de conexión con Pearl AI |
| `503` | Service Unavailable | Servicio temporalmente no disponible |

### **Manejo de Errores**

Todos los endpoints devuelven errores en formato JSON consistente:

```json
{
  "success": false,
  "error": "Descripción del error",
  "timestamp": "2025-09-03T16:30:45.123456",
  "details": {
    "error_code": "PEARL_CONNECTION_ERROR",
    "suggestion": "Verifica las credenciales de Pearl AI"
  }
}
```

### **Parámetros de Query Comunes**

**GET /api/calls/leads** admite:
- `limit`: Número de resultados por página (default: 50, max: 500)
- `offset`: Número de registros a saltar (default: 0)  
- `city`: Filtro por ciudad
- `status`: Filtro por estado de llamada (`no_selected`, `selected`, `calling`, `completed`, `error`)
- `priority`: Filtro por prioridad (1-5)
- `selected_only`: Solo leads seleccionados (`true`/`false`)

**Ejemplo**: `/api/calls/leads?city=Madrid&status=selected&limit=100&priority=1`

## 🏗️ Arquitectura del Sistema

### **Componentes Backend**
- **`pearl_caller.py`** - Cliente de Pearl AI
- **`call_manager.py`** - Gestor de cola y llamadas concurrentes
- **`api_pearl_calls.py`** - API REST endpoints
- **`db_migration_add_call_fields.py`** - Migración de base de datos

### **Componentes Frontend**
- **`templates/calls_manager.html`** - Interfaz principal
- **`static/css/calls_manager.css`** - Estilos personalizados
- **`static/js/calls_manager.js`** - Funcionalidad cliente

### **Base de Datos**
```sql
-- Nuevos campos añadidos a la tabla 'leads'
call_status ENUM('no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer')
call_priority INT DEFAULT 3
selected_for_calling BOOLEAN DEFAULT FALSE
pearl_outbound_id VARCHAR(100)
last_call_attempt DATETIME
call_attempts_count INT DEFAULT 0
call_error_message TEXT
pearl_call_response TEXT
call_notes TEXT
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
```

## ⚙️ Configuración Avanzada

### **Llamadas Simultáneas**
Configura el número máximo de llamadas concurrentes:
```python
# En call_manager.py
manager = CallManager(max_concurrent_calls=5)
```

### **Frecuencia de Actualización**
```javascript
// En calls_manager.js
this.config = {
    refreshInterval: 3000, // 3 segundos cuando inactivo
    activeRefreshInterval: 1000 // 1 segundo cuando activo
};
```

### **Reintentos y Timeouts**
```python
# En pearl_caller.py
@dataclass
class CallTask:
    max_attempts: int = 3
    timeout: int = 30
```
 
- **scheduled_calls_interval_minutes**: Intervalo en minutos para ejecutar el daemon de llamadas programadas.

## 🧪 Testing y Validación

### **Testing Manual de APIs**

Ejecuta las pruebas automatizadas de endpoints:
```bash
cd /ruta/a/tuotempo
python test_calls_endpoints.py
```

### **Prueba Individual de Endpoints**

```bash
# Verificar estado del sistema
curl -X GET http://localhost:8080/api/calls/status

# Obtener leads con filtros
curl -X GET "http://localhost:8080/api/calls/leads?limit=5&city=Madrid"

# Probar conexión Pearl AI
curl -X GET http://localhost:8080/api/calls/test/connection

# Obtener configuración
curl -X GET http://localhost:8080/api/calls/configuration

# Probar API de resultado de llamadas
curl -X GET http://localhost:8080/api/status
curl -X GET http://localhost:8080/api/leads_reserva_automatica
curl -X GET "http://localhost:8080/api/obtener_resultados?limit=5"

# Actualizar resultado de llamada (POST)
curl -X POST http://localhost:8080/api/actualizar_resultado \
  -H "Content-Type: application/json" \
  -d '{"telefono":"699106495","volverALlamar":true,"razonvueltaallamar":"Cliente ocupado"}'

# Obtener historial de llamadas
curl -X GET http://localhost:8080/api/calls/history

# Obtener estadísticas de llamadas
curl -X GET http://localhost:8080/api/calls/history/stats

# Obtener llamadas programadas
curl -X GET http://localhost:8080/api/calls/schedule

# Filtrar llamadas programadas por estado
curl -X GET "http://localhost:8080/api/calls/schedule?status=pending"

# Obtener historial filtrado por fechas
curl -X GET "http://localhost:8080/api/calls/history?from_date=2025-09-08&limit=10"
```

### **Testing del Actualizador de Llamadas**

```bash
# Ejecutar un ciclo manual del actualizador
python -c "from calls_updater import update_calls_from_pearl; update_calls_from_pearl()"

# Verificar logs del actualizador
tail -f logs/calls_updater.log
```

### **Validación del Sistema Completo**

1. **Servidor activo**: `python start.py`
2. **APIs respondiendo**: Ejecutar `test_calls_endpoints.py`
3. **Pearl AI conectado**: Verificar `/api/calls/test/connection`
4. **Base de datos sincronizada**: Revisar campos `call_*` en tabla leads
5. **Interfaz funcional**: Acceder a `http://localhost:8080/calls-manager`

## 🔧 Troubleshooting

### **Error: No se puede conectar con Pearl AI**
1. Verifica las credenciales en `.env`
2. Prueba la conexión: `GET /api/calls/test/connection`
3. Revisa logs en la consola del servidor

### **Error: Leads no se cargan**
1. Ejecuta la migración de base de datos
2. Verifica permisos de usuario
3. Revisa conexión MySQL

### **Error: Llamadas no inician**
1. Selecciona leads primero
2. Verifica outbound ID configurado
3. Comprueba números de teléfono válidos

## 📈 Estadísticas y Métricas

El sistema proporciona métricas en tiempo real:
- **Total de llamadas** realizadas
- **Llamadas exitosas** vs fallidas
- **Llamadas activas** en este momento
- **Progreso** de la cola de llamadas
- **Tasa de éxito** por campaña

## 🔐 Seguridad

- **Autenticación requerida** para todas las rutas
- **Validación de entrada** en todas las APIs
- **Manejo seguro** de credenciales
- **Logs detallados** para auditoría

## 📞 Soporte

Para problemas o consultas:
1. Revisa los logs del servidor
2. Consulta la documentación de Pearl AI
3. Verifica la configuración de base de datos

## 🎉 Próximas Mejoras

- [ ] Integración con WebSockets para actualizaciones en tiempo real
- [ ] Sistema de reportes avanzados
- [ ] Integración con calendarios para agendar citas
- [ ] Machine Learning para optimizar horarios de llamada
- [ ] Grabación y transcripción automática de llamadas
- [ ] Dashboard de analíticas avanzadas

---

**Desarrollado para TuoTempo** 
*Sistema de gestión de llamadas médicas automatizado con IA*

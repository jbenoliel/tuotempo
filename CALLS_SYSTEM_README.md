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

### **Control de Llamadas**
```http
POST /api/calls/start
POST /api/calls/stop
```

### **Gestión de Leads**
```http
GET /api/calls/leads?city=Madrid&status=selected&limit=50
POST /api/calls/leads/select
POST /api/calls/leads/reset
```

### **Pearl AI**
```http
GET /api/calls/pearl/campaigns
GET /api/calls/test/connection
```

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

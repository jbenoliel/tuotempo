# Sistema de Llamadas Programadas - Documentación

## Descripción General

El sistema de llamadas programadas gestiona automáticamente la reprogramación de llamadas según los resultados obtenidos. Permite manejar reintentos, horarios laborables y cierre automático de leads después del máximo de intentos.

## Componentes Principales

### 1. Tabla `call_schedule`
**Propósito**: Almacena las llamadas programadas para ejecutar en el futuro.

**Campos importantes**:
- `lead_id`: ID del lead a llamar
- `scheduled_at`: Fecha y hora programada para la llamada
- `attempt_number`: Número de intento (1, 2, 3...)
- `status`: Estado ('pending', 'completed', 'cancelled')
- `last_outcome`: Último resultado de llamada ('no_answer', 'busy', 'hang_up')

### 2. Tabla `scheduler_config`
**Propósito**: Configuración del sistema de reprogramación.

**Estructura**:
- `config_key`: Clave de configuración
- `config_value`: Valor de configuración
- `description`: Descripción de la configuración

**Configuraciones disponibles**:
- `default_delay_hours`: Horas de retraso por defecto (4)
- `default_max_attempts`: Máximo intentos por defecto (3)
- `no_answer_delay_hours`: Retraso específico para no_answer
- `busy_delay_hours`: Retraso específico para busy
- `hang_up_delay_hours`: Retraso específico para hang_up

## Archivos del Sistema

### `reprogramar_llamadas_simple.py`
**Función principal**: `simple_reschedule_failed_call(lead_id: int, outcome: str) -> bool`

**Responsabilidades**:
- Lee configuración de reintentos desde `scheduler_config`
- **✅ Respeta días laborables y horarios de trabajo**
- **✅ No reprograma leads cerrados**
- **✅ Cancela programaciones pendientes para leads cerrados**
- Valida número de intentos actuales vs máximo permitido
- Calcula próxima fecha/hora de intento respetando horarios laborables
- Actualiza contador de intentos en leads
- Crea nuevo registro en `call_schedule`
- Cierra lead si excede máximo de intentos

**Funciones adicionales**:
- `cancel_scheduled_calls_for_lead(lead_id, reason)` - Cancela llamadas programadas
- `cleanup_closed_leads_schedules()` - Limpieza masiva de leads cerrados
- `calculate_next_working_datetime(base, delay)` - Cálculo de horarios laborables

**Ejemplo de uso**:
```python
from reprogramar_llamadas_simple import simple_reschedule_failed_call

# Reprogramar llamada fallida
resultado = simple_reschedule_failed_call(123, 'no_answer')
if resultado:
    print("Lead reprogramado para próximo intento")
else:
    print("Lead cerrado por máximo intentos")
```

### `call_manager_scheduler_integration.py`
**Función principal**: `enhanced_process_call_result(lead_id: int, call_result: Dict, pearl_response: Dict = None)`

**Responsabilidades**:
- **✅ Cancela automáticamente llamadas programadas antes de procesar resultado**
- Procesa resultados de llamadas de Pearl AI
- Integra automáticamente con el sistema de reprogramación
- Maneja llamadas exitosas y fallidas
- Extrae información de citas cuando está disponible

**Regla de negocio implementada**:
- Al procesar cualquier llamada (programada o manual), cancela automáticamente todas las programaciones pendientes para ese lead

### `probar_llamadas_programadas.py`
**Propósito**: Script de prueba y monitoreo del sistema

**Funciones disponibles**:
- `mostrar_estadisticas_call_schedule()`: Estadísticas generales
- `mostrar_llamadas_pendientes(limit)`: Lista de próximas llamadas
- `simular_proceso_llamada_exitosa()`: Simula llamada exitosa
- `simular_proceso_llamada_fallida()`: Simula llamada fallida
- `probar_reprogramacion_automatica()`: Prueba reprogramación

## Flujo de Funcionamiento

### 1. Llamada Fallida
```
Lead recibe llamada → Resultado = "no_answer/busy/hang_up"
↓
enhanced_process_call_result() procesa resultado
↓
simple_reschedule_failed_call() se ejecuta
↓
¿Intentos < Máximo? → SÍ: Crear schedule → NO: Cerrar lead
↓
Nuevo registro en call_schedule con scheduled_at = NOW() + delay_hours
```

### 2. Procesamiento de Llamadas Programadas
```
Sistema consulta call_schedule
↓
WHERE status = 'pending' AND scheduled_at <= NOW()
↓
Para cada llamada pendiente:
  - Realizar llamada (Pearl AI)
  - Procesar resultado
  - Marcar schedule como 'completed'
  - Si falla: Reprogramar nuevamente
```

### 3. Configuración de Reintentos
```
simple_reschedule_failed_call(lead_id, 'no_answer')
↓
get_retry_config_from_db('no_answer')
↓
Busca en scheduler_config:
  1. no_answer_delay_hours + no_answer_max_attempts
  2. Si no existe: default_delay_hours + default_max_attempts
  3. Si no existe: Valores hardcoded (4 horas, 3 intentos)
```

## Estados de Call Schedule

| Estado | Descripción |
|--------|-------------|
| `pending` | Llamada programada esperando ejecución |
| `completed` | Llamada ya procesada (exitosa o fallida) |
| `cancelled` | Llamada cancelada (lead cerrado, etc.) |

## Estados de Call Status (enum en leads)

| Estado | Descripción |
|--------|-------------|
| `no_selected` | Lead no seleccionado para llamar |
| `selected` | Lead seleccionado para llamar |
| `calling` | Llamada en curso |
| `completed` | Llamada completada exitosamente |
| `error` | Error en la llamada |
| `busy` | Línea ocupada |
| `no_answer` | No respondió |

## Configuración de Horarios

### Configuraciones disponibles en scheduler_config:
- `working_hours_start`: Hora inicio laboral (ej: "10:00")
- `working_hours_end`: Hora fin laboral (ej: "20:00")
- `working_days`: Días laborables (ej: "1,2,3,4,5" = Lunes a Viernes)

## Queries Importantes

### Obtener llamadas pendientes:
```sql
SELECT cs.id, cs.lead_id, cs.scheduled_at, cs.attempt_number,
       l.nombre, l.apellidos, l.telefono
FROM call_schedule cs
JOIN leads l ON cs.lead_id = l.id
WHERE cs.status = 'pending'
  AND cs.scheduled_at <= NOW()
  AND (l.lead_status IS NULL OR l.lead_status = 'open')
  AND (l.manual_management IS NULL OR l.manual_management = FALSE)
ORDER BY cs.scheduled_at ASC, cs.attempt_number ASC;
```

### Estadísticas del sistema:
```sql
-- Distribución por status
SELECT status, COUNT(*) as total
FROM call_schedule
GROUP BY status;

-- Llamadas pendientes ahora
SELECT COUNT(*) as total
FROM call_schedule cs
JOIN leads l ON cs.lead_id = l.id
WHERE cs.status = 'pending'
  AND cs.scheduled_at <= NOW()
  AND (l.lead_status IS NULL OR l.lead_status = 'open');
```

## Monitoreo y Troubleshooting

### Verificar sistema:
```bash
# Ejecutar pruebas completas
python probar_llamadas_programadas.py

# Verificar solo estadísticas
python -c "from probar_llamadas_programadas import mostrar_estadisticas_call_schedule; mostrar_estadisticas_call_schedule()"
```

### Problemas comunes:

1. **Error "Data truncated for column 'call_status'"**
   - **Causa**: Valor no válido para enum call_status
   - **Solución**: Usar solo valores válidos: 'no_selected', 'selected', 'calling', 'completed', 'error', 'busy', 'no_answer'

2. **Error "none_dealloc"**
   - **Causa**: Problema con mysql-connector-python
   - **Solución**: Usar pymysql en su lugar (ya implementado)

3. **Leads no se reprograman**
   - **Verificar**: Configuración en scheduler_config
   - **Verificar**: Estado del lead (debe ser 'open')
   - **Verificar**: Número de intentos < máximo

### Logs importantes:
```python
# Activar logging detallado
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## Integración con Pearl AI

El sistema se integra automáticamente cuando Pearl AI retorna resultados de llamadas:

```python
# En call_manager_scheduler_integration.py
enhanced_process_call_result(lead_id, {
    'callResult': 'no_answer',
    'status': 'failed',
    'outcome': 'no_answer'
})
```

## Seguridad y Buenas Prácticas

1. **Validación de parámetros**: Siempre validar lead_id y outcome
2. **Transacciones**: Usar commits/rollbacks para consistencia
3. **Conexiones**: Cerrar siempre las conexiones de BD
4. **Logging**: Registrar todas las operaciones importantes
5. **Testing**: Usar modo simulación para pruebas

## Mantenimiento

### Limpieza periódica:
```sql
-- Limpiar schedules antiguos cancelados (mensual)
DELETE FROM call_schedule 
WHERE status = 'cancelled' 
  AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Verificar schedules huérfanos
SELECT cs.* FROM call_schedule cs
LEFT JOIN leads l ON cs.lead_id = l.id
WHERE l.id IS NULL;
```

### Limpieza automática de leads cerrados:
```python
# Ejecutar limpieza diaria
from reprogramar_llamadas_simple import cleanup_closed_leads_schedules
cancelled = cleanup_closed_leads_schedules()
print(f"Limpieza automática: {cancelled} llamadas canceladas")
```

### Actualización de configuración:
```sql
-- Cambiar delay por defecto a 2 horas
INSERT INTO scheduler_config (config_key, config_value, description)
VALUES ('default_delay_hours', '2', 'Horas de retraso por defecto')
ON DUPLICATE KEY UPDATE config_value = '2';
```

---

**Última actualización**: 2025-09-14
**Versión**: 1.0
**Responsable**: Sistema automatizado de llamadas
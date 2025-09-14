# Reglas de Negocio - Sistema de Llamadas Programadas

## Descripción General

Este documento define las reglas de negocio implementadas en el sistema de llamadas programadas para garantizar la coherencia de datos y evitar llamadas innecesarias o duplicadas.

---

## Regla #1: No Reprogramar Leads Cerrados

### **Descripción**
No se deben crear nuevas programaciones de llamadas para leads que ya están cerrados.

### **Justificación**
- Los leads cerrados no requieren más seguimiento
- Evita trabajo innecesario del call center
- Mantiene limpia la cola de llamadas programadas
- Mejora la eficiencia del sistema

### **Implementación**
```python
def simple_reschedule_failed_call(lead_id: int, outcome: str) -> bool:
    # Verificar estado del lead
    if lead['lead_status'] == 'closed':
        logger.info(f"Lead {lead_id} ya está cerrado - no se reprograma")
        # Cancelar cualquier llamada programada pendiente
        cursor.execute("""
            UPDATE call_schedule 
            SET status = 'cancelled', updated_at = NOW()
            WHERE lead_id = %s AND status = 'pending'
        """, (lead_id,))
        return False
```

### **Comportamiento**
- ✅ **Cuando se intenta reprogramar un lead cerrado:**
  - No se crea nueva programación
  - Se cancelan automáticamente las programaciones pendientes existentes
  - Se registra en logs la razón del rechazo
  - Función retorna `False`

### **Estados de lead considerados cerrados**
- `lead_status = 'closed'`

---

## Regla #2: Cancelar Programaciones al Realizar Llamada No Programada

### **Descripción**
Cuando se realiza cualquier llamada a un lead (programada o no programada), se deben cancelar automáticamente todas las llamadas programadas pendientes para ese lead.

### **Justificación**
- Evita duplicar esfuerzos de llamadas
- Una llamada manual/inmediata tiene prioridad sobre las programadas
- Previene confusión en el call center
- Mantiene coherencia en el seguimiento del lead

### **Implementación**
```python
def enhanced_process_call_result(lead_id: int, call_result: Dict, pearl_response: Dict = None):
    # Al procesar CUALQUIER llamada, cancelar programaciones pendientes
    cancelled_count = cancel_scheduled_calls_for_lead(lead_id, 
        "Llamada realizada - cancelando programaciones pendientes")
    
    if cancelled_count > 0:
        logger.info(f"Canceladas {cancelled_count} llamadas programadas para lead {lead_id}")
```

### **Comportamiento**
- ✅ **Antes de procesar el resultado de cualquier llamada:**
  1. Buscar llamadas programadas pendientes para el lead
  2. Cambiar status de `'pending'` a `'cancelled'`
  3. Actualizar timestamp de modificación
  4. Registrar en logs la cantidad cancelada
  5. Continuar procesando el resultado de la llamada actual

### **Aplicación**
- Se ejecuta para **todas las llamadas**, independientemente de:
  - Si la llamada fue programada o manual
  - El resultado de la llamada (exitosa, fallida, busy, etc.)
  - El origen de la llamada (Pearl AI, manual, etc.)

---

## Regla #3: Limpieza Automática de Leads Cerrados

### **Descripción**
El sistema debe incluir funciones de mantenimiento para limpiar regularmente las llamadas programadas para leads que fueron cerrados después de ser programadas.

### **Justificación**
- Los leads pueden cerrarse por otros procesos después de ser programados
- Limpieza preventiva para mantener eficiencia del sistema
- Evita procesamiento innecesario de llamadas

### **Implementación**
```python
def cleanup_closed_leads_schedules() -> int:
    """Cancela llamadas programadas para leads cerrados"""
    cursor.execute("""
        UPDATE call_schedule cs
        JOIN leads l ON cs.lead_id = l.id
        SET cs.status = 'cancelled', cs.updated_at = NOW()
        WHERE cs.status = 'pending' 
            AND l.lead_status = 'closed'
    """)
    return cursor.rowcount
```

### **Uso Recomendado**
- Ejecutar diariamente como tarea de mantenimiento
- Ejecutar antes de obtener lista de llamadas pendientes
- Incluir en scripts de limpieza periódica

---

## Funciones Utilitarias

### `cancel_scheduled_calls_for_lead(lead_id, reason)`
**Propósito**: Cancela todas las llamadas programadas pendientes para un lead específico.

**Parámetros**:
- `lead_id` (int): ID del lead
- `reason` (str): Razón de la cancelación para logs

**Retorna**: Número de llamadas canceladas

**Uso**:
```python
# Cancelar por llamada manual
cancelled = cancel_scheduled_calls_for_lead(123, "Llamada manual realizada")

# Cancelar por cierre de lead
cancelled = cancel_scheduled_calls_for_lead(456, "Lead cerrado por no interés")
```

### `cleanup_closed_leads_schedules()`
**Propósito**: Limpieza masiva de llamadas para leads cerrados.

**Retorna**: Número total de llamadas canceladas

**Uso**:
```python
# Limpieza diaria
cancelled_total = cleanup_closed_leads_schedules()
logger.info(f"Limpieza diaria: {cancelled_total} llamadas canceladas")
```

---

## Impacto en el Flujo de Trabajo

### **Antes de las Reglas**
```
Lead programado → Llamada manual → Llamada programada se ejecuta después
                                 ↓
                              DUPLICACIÓN
```

### **Después de las Reglas**
```
Lead programado → Llamada manual → Programaciones canceladas automáticamente
                                 ↓
                              SIN DUPLICACIÓN
```

---

## Logs y Monitoreo

### **Logs Importantes**
- `"Lead {id} ya está cerrado - no se reprograma"`
- `"Canceladas {count} llamadas programadas para lead {id}: {reason}"`
- `"Canceladas {count} llamadas programadas para leads cerrados"`

### **Métricas Recomendadas**
- Número de intentos de reprogramación rechazados por lead cerrado
- Número de llamadas canceladas por llamada no programada
- Frecuencia de limpieza de leads cerrados

---

## Estados de Call Schedule

| Estado | Descripción | Cuándo se Usa |
|--------|-------------|---------------|
| `pending` | Llamada programada esperando ejecución | Estado inicial |
| `completed` | Llamada ejecutada (exitosa o fallida) | Después de ejecutar |
| `cancelled` | Llamada cancelada por reglas de negocio | Por las reglas implementadas |

---

## Casos de Uso Ejemplos

### **Caso 1: Lead cerrado después de programación**
```
1. Lead 123 se programa para mañana 10:00
2. Supervisor cierra Lead 123 manualmente (no interesado)
3. Sistema ejecuta limpieza → Cancela programación automáticamente
4. Mañana a las 10:00 → No se intenta llamar al lead cerrado
```

### **Caso 2: Llamada manual durante programación pendiente**
```
1. Lead 456 programado para 15:00
2. Agente llama manualmente a las 14:00
3. Sistema cancela automáticamente la programación de las 15:00
4. Se procesa resultado de llamada manual
5. Si falla, se reprograma según configuración normal
```

### **Caso 3: Intento de reprogramar lead cerrado**
```
1. Llamada falla para Lead 789
2. Sistema intenta reprogramar automáticamente
3. Detecta que Lead 789 está cerrado
4. No crea nueva programación
5. Cancela cualquier programación pendiente
6. Registra en logs el rechazo
```

---

## Mantenimiento y Verificación

### **Script de Verificación**
```bash
# Ejecutar verificación completa
python limpiar_llamadas_leads_cerrados.py
```

### **Consulta SQL de Auditoria**
```sql
-- Verificar llamadas para leads cerrados (no debería devolver resultados)
SELECT cs.*, l.lead_status, l.closure_reason
FROM call_schedule cs
JOIN leads l ON cs.lead_id = l.id
WHERE cs.status = 'pending' 
  AND l.lead_status = 'closed';
```

---

**Implementado**: 2025-09-14  
**Versión**: 1.0  
**Archivos Modificados**:
- `reprogramar_llamadas_simple.py`
- `call_manager_scheduler_integration.py`  
- `limpiar_llamadas_leads_cerrados.py`
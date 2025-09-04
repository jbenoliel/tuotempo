# 📋 Manual de Usuario - TuoTempo

## Índice
1. [Dashboard Principal](#dashboard-principal)
2. [Actualización de Leads](#actualización-de-leads)
3. [Acceso y Navegación](#acceso-y-navegación)

---

## Dashboard Principal
*Ruta: `/` o página principal*

### 🎯 Propósito
El dashboard proporciona una vista general en tiempo real del estado de las llamadas y gestión de leads, con métricas clave y gráficos interactivos.

### 📊 Métricas Principales

#### Fila Superior - Métricas Básicas:
- **Total leads**: Número total de contactos en el sistema
- **Leads contactados**: Cantidad de leads que han sido contactados exitosamente  
- **Tasa contacto**: Porcentaje de contacto sobre total de leads
- **% Citas / Contactados**: Porcentaje de citas agendadas sobre contactados

#### Fila Inferior - Estados Específicos:
- **Citas agendadas**: Número total de citas programadas (con y sin pack)
- **Volver a llamar**: Leads que requieren un segundo contacto
- **No interesados**: Leads que han rechazado el servicio

### 🎛️ Filtros y Controles

#### Filtro por Archivo de Origen:
- **Ubicación**: Parte superior de la página
- **Función**: Permite filtrar todas las métricas por archivo específico de importación
- **Opciones**:
  - 📊 **Todos los archivos**: Vista global sin filtros
  - 📁 **Archivos individuales**: Cada archivo con su cantidad de leads
  
**Cómo usar:**
1. Hacer clic en el selector desplegable
2. Elegir uno o varios archivos (permite selección múltiple)
3. Hacer clic en "Actualizar" para aplicar filtros
4. Usar "Limpiar" para volver a la vista completa

### 📈 Gráficos y Visualizaciones

#### 1. Distribución de Estados (Gráfico Circular):
- **Muestra**: Proporción entre citas agendadas, volver a llamar y no interesados
- **Colores**: 
  - 🟢 Verde: Citas agendadas
  - 🟡 Amarillo: Volver a llamar  
  - 🔴 Rojo: No interesados

#### 2. Subestados - Volver a Llamar (Gráfico Barras):
- **Muestra**: Desglose detallado de motivos para volver a llamar
- **Categorías**:
  - No disponible cliente
  - Buzón de voz
  - Problema técnico
  - Cortado

#### 3. Subestados - No Interesado (Gráfico Barras):
- **Muestra**: Razones específicas de desinterés
- **Categorías**:
  - No disponibilidad cliente
  - Descontento con Adeslas
  - Próxima baja
  - No da motivos

#### 4. Subestados - Citas (Gráfico Barras):
- **Muestra**: Distribución de citas por tipo de pack
- **Categorías**:
  - Con Pack: Citas con servicios adicionales
  - Sin Pack: Citas básicas

### ⚡ Actualización Automática
- Los datos se actualizan automáticamente al recargar la página
- Los filtros mantienen la selección entre recargas
- Cache optimizado para carga rápida

### 💡 Tips de Uso
1. **Filtros múltiples**: Puedes seleccionar varios archivos manteniendo Ctrl presionado
2. **Vista comparativa**: Usa filtros para comparar rendimiento entre diferentes campañas
3. **Interpretación rápida**: Los porcentajes te dan una idea inmediata de eficiencia
4. **Seguimiento temporal**: Recarga periódicamente para ver evolución en tiempo real

---

## Actualización de Leads
*Ruta: `/admin/update-leads`*

### 🎯 Propósito
Herramienta administrativa para buscar, visualizar y actualizar información específica de leads individuales. Permite gestión manual granular de contactos.

### 🔍 Búsqueda de Leads

#### Función de Búsqueda:
- **Criterios**: Teléfono, nombre, apellido
- **Mínimo**: 2 caracteres para activar búsqueda
- **Resultados**: Hasta 20 leads por búsqueda
- **Búsqueda**: Clic en "Buscar" o presionar Enter

#### Información Mostrada en Resultados:
| Campo | Descripción |
|-------|-------------|
| **Nombre** | Nombre completo del lead |
| **Teléfono** | Número principal de contacto |
| **Ciudad** | Ubicación geográfica |
| **Estado 1** | Estado principal (Cita Agendada, Volver a llamar, etc.) |
| **Estado 2** | Subestado específico |
| **Gestión** | Tipo: Manual (👤) o Automático (🤖) |
| **Llamadas** | Número de intentos realizados |
| **Acciones** | Botón "Editar" para modificar |

### ✏️ Formulario de Actualización

#### Información Básica:
1. **Teléfono** *(Solo lectura)*
   - Campo protegido que no se puede modificar

2. **Buzón de Voz**
   - ✅ **Sí**: La llamada cayó en buzón
   - ❌ **No**: El contacto contestó
   - ⚪ **No especificado**: Sin información

3. **¿Volver a llamar?**
   - ✅ **Sí**: Requiere nuevo contacto
   - ❌ **No**: No contactar nuevamente
   - ⚪ **No especificado**: Sin decisión

4. **Tipo de Gestión** ⚠️ *Campo Crítico*
   - 🤖 **Automática**: El sistema gestiona las llamadas
   - 👤 **Manual**: Excluye del sistema automático
   - ⚪ **No cambiar**: Mantiene configuración actual

#### Códigos y Estados:

5. **Código No Interés**
   - No disponibilidad cliente
   - Descontento con Adeslas  
   - Próxima baja
   - No da motivos

6. **Código Volver a Llamar**
   - Buzón
   - No disponible cliente
   - Interesado. Problema técnico

7. **Fecha de Cita** *(Formato: DD/MM/AAAA)*
   - Campo de fecha para agendar citas

8. **Hora de Cita** *(Formato: HH:MM)*
   - Campo de hora específica

### 🔄 Flujo de Trabajo Completo

#### Paso 1: Localizar Lead
1. Ir a `/admin/update-leads`
2. Escribir criterio de búsqueda (mínimo 2 caracteres)
3. Presionar "Buscar" o Enter
4. Revisar resultados en la tabla

#### Paso 2: Seleccionar Lead
1. Identificar el lead correcto en los resultados
2. Hacer clic en "Editar" en la columna Acciones
3. Se abre el formulario de actualización pre-rellenado

#### Paso 3: Actualizar Información
1. Modificar solo los campos necesarios
2. Usar "No especificado" o "No cambiar" para campos sin modificación
3. Verificar que los datos sean correctos

#### Paso 4: Guardar Cambios
1. Hacer clic en "Actualizar Lead"
2. Confirmar el mensaje de éxito
3. Los cambios se aplican inmediatamente

### ⚠️ Consideraciones Importantes

#### Gestión Manual vs Automática:
- **Manual (👤)**: El lead se EXCLUYE completamente del sistema de llamadas automáticas
- **Automática (🤖)**: El lead permanece en el sistema automatizado
- **Uso**: Cambiar a manual solo para casos especiales que requieren atención personal

#### Impacto de los Cambios:
- Los cambios son **inmediatos** y **permanentes**
- Afectan las estadísticas del dashboard en tiempo real
- Los leads en gestión manual no aparecerán en colas automáticas

### 💡 Casos de Uso Comunes

#### Scenario 1: Lead Contactado Manualmente
1. Buscar el lead por teléfono
2. Actualizar "Volver a llamar" → No
3. Si agendó cita: Completar fecha y hora
4. Cambiar gestión a "Manual" si requiere seguimiento personal

#### Scenario 2: Corrección de Estado
1. Localizar lead con estado incorrecto
2. Actualizar código correspondiente (No Interés o Volver a Llamar)
3. Ajustar tipo de gestión según necesidad

#### Scenario 3: Exclusión de Llamadas Automáticas  
1. Buscar leads problemáticos o especiales
2. Cambiar gestión a "Manual"
3. Esto previene llamadas automáticas futuras

### 🎯 Tips de Eficiencia
- Usa búsquedas específicas para localizar leads rápidamente
- Actualiza solo los campos necesarios para mantener integridad
- Revisa el impacto en las métricas del dashboard después de cambios masivos
- Documenta cambios importantes para seguimiento futuro

---

## Acceso y Navegación

### 🔗 URLs Principales
- **Dashboard**: `https://web-production-b743.up.railway.app/`
- **Actualización Leads**: `https://web-production-b743.up.railway.app/admin/update-leads`

### 🔐 Autenticación
Ambas páginas requieren autenticación de usuario para acceso.

### 📱 Compatibilidad
- **Navegadores**: Chrome, Firefox, Safari, Edge (últimas versiones)
- **Dispositivos**: Desktop, tablet, móvil (diseño responsivo)
- **Resoluciones**: Optimizado para pantallas desde 320px hasta 4K

---

*Manual generado para TuoTempo v1.0 - Sistema de Gestión de Llamadas*
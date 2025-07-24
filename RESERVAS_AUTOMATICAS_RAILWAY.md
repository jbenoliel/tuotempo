# Sistema de Reservas Automáticas - Configuración Railway

## ✅ Implementación Completada

El sistema de reservas automáticas está completamente integrado y listo para funcionar en Railway.

### 🔧 Configuración Requerida en Railway

El sistema funciona con las **variables de TuoTempo ya existentes** en tu proyecto. Si quieres personalizar la configuración, puedes añadir estas variables opcionales:

```bash
# Variables OPCIONALES de TuoTempo (el sistema tiene valores predeterminados)
TUOTEMPO_ENV=PRO                      # PRO o PRE (default: PRO)
TUOTEMPO_API_KEY_PRO=tu_api_key       # API key personalizada para PRO
TUOTEMPO_API_KEY_PRE=tu_api_key       # API key personalizada para PRE
TUOTEMPO_API_SECRET_PRO=tu_secret     # API secret personalizado
TUOTEMPO_INSTANCE_ID=tt_portal_adeslas # Instance ID personalizado
TUOTEMPO_ACTIVITY_ID=sc159232371eb9c1 # Activity ID personalizado

# Variables OPCIONALES del daemon
RESERVAS_DAEMON_ENABLED=true          # Habilitar/deshabilitar daemon (default: true)
RESERVAS_INTERVAL_MINUTES=30          # Intervalo en minutos (default: 30)
```

**Nota importante**: Si no configuras las variables de TuoTempo, el sistema usará las credenciales predeterminadas integradas en el código.

### 🚀 Funcionamiento Automático

1. **Migración automática**: Los campos se añaden automáticamente al desplegar
2. **Daemon integrado**: Se ejecuta como hilo en segundo plano en el servicio principal
3. **Sin servicios adicionales**: Todo funciona dentro del servicio web existente

### 📊 Campos Añadidos Automáticamente

La migración añade estos campos a la tabla `leads`:

```sql
-- Campos para reservas automáticas
`reserva_automatica` BOOLEAN DEFAULT FALSE,
`preferencia_horario` ENUM('mañana', 'tarde') DEFAULT 'mañana',
`fecha_minima_reserva` DATE NULL,

-- Índices optimizados
CREATE INDEX idx_reserva_automatica ON leads(reserva_automatica);
CREATE INDEX idx_fecha_minima_reserva ON leads(fecha_minima_reserva);
CREATE INDEX idx_reserva_auto_fecha ON leads(reserva_automatica, fecha_minima_reserva);
```

### 🔄 API Actualizada

El endpoint `/api/actualizar_resultado` ahora acepta:

```json
{
  "telefono": "612345678",
  "reservaAutomatica": true,
  "preferenciaHorario": "mañana",  // opcional, default: "mañana"
  "fechaMinimaReserva": "30/07/2024"  // opcional, default: hoy + 15 días
}
```

### 📈 Logs del Sistema

En Railway verás logs como estos:

```
[RESERVAS-DAEMON] Iniciando daemon de reservas automáticas...
[RESERVAS-DAEMON] Daemon iniciado con intervalo de 30 minutos
[RESERVAS-DAEMON] --- Iniciando ciclo: 2024-07-24 17:30:00 ---
Encontrados 5 leads marcados para reserva automática
Procesando lead 123: Juan Pérez
Reserva realizada exitosamente para lead 123
[RESERVAS-DAEMON] --- Ciclo completado en 45.32 segundos ---
[RESERVAS-DAEMON] Esperando 30 minutos...
```

### 🛠️ Control del Sistema

#### Deshabilitar temporalmente:
```bash
RESERVAS_DAEMON_ENABLED=false
```

#### Cambiar intervalo:
```bash
RESERVAS_INTERVAL_MINUTES=60  # Cada hora
```

#### Verificar estado:
- GET `/api/leads_reserva_automatica` - Ver leads marcados
- Logs de Railway - Monitorear actividad del daemon

### 🔐 Seguridad

- ✅ No hardcodea credenciales
- ✅ Usa variables de entorno de Railway
- ✅ Manejo robusto de errores
- ✅ Auto-recuperación de fallos temporales

### 📞 Endpoints Disponibles

1. **Marcar lead para reserva automática**:
   ```bash
   POST /api/actualizar_resultado
   {
     "telefono": "612345678",
     "reservaAutomatica": true,
     "preferenciaHorario": "tarde",
     "fechaMinimaReserva": "01/08/2024"
   }
   ```

2. **Consultar leads marcados**:
   ```bash
   GET /api/leads_reserva_automatica
   ```

3. **Actualizar resultado y marcar**:
   ```bash
   POST /api/actualizar_resultado
   {
     "telefono": "612345678",
     "volverALlamar": true,
     "reservaAutomatica": true
   }
   ```

## 🎯 Resumen

- ✅ **Migración automática** - Los campos se crean al desplegar
- ✅ **Daemon integrado** - Funciona en el servicio principal
- ✅ **API actualizada** - Acepta parámetros de reservas automáticas
- ✅ **Sin configuración adicional** - Usa las credenciales TuoTempo existentes
- ✅ **Configuración flexible** - Control opcional vía variables de entorno
- ✅ **Logs detallados** - Monitoreo completo en Railway
- ✅ **Manejo de errores** - Sistema robusto y auto-recuperable

**¡El sistema está listo para usar en producción sin configuración adicional!** 🚀

# Plan de Testing Local - Sistema de Reservas Automáticas y Monitoreo

## 📋 **Objetivo**
Testear completamente el sistema de reservas automáticas, monitoreo del daemon y verificación de servicios Railway en entorno local antes del despliegue en producción.

## 🔧 **Preparación del Entorno Local**

### **1. Configuración de Base de Datos**
```bash
# Verificar que MySQL esté ejecutándose
mysql -u root -p

# Crear base de datos de testing si no existe
CREATE DATABASE IF NOT EXISTS tuotempo_test;
USE tuotempo_test;

# Verificar que las tablas existen (especialmente la nueva tabla daemon_status)
SHOW TABLES;
DESCRIBE daemon_status;
```

### **2. Variables de Entorno**
Crear/verificar archivo `.env` con:
```env
# Base de datos local
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password
DB_DATABASE=tuotempo_test

# TuoTempo API (usar credenciales de prueba)
TUOTEMPO_ENV=PRE
TUOTEMPO_API_KEY_PRE=3a5835be0f540c7591c754a2bf0758bb
TUOTEMPO_API_SECRET_PRE=default_secret
TUOTEMPO_INSTANCE_ID=tt_portal_adeslas

# Daemon de reservas automáticas
RESERVAS_DAEMON_ENABLED=true
RESERVAS_INTERVAL_MINUTES=1

# Flask
FLASK_ENV=development
FLASK_DEBUG=true
```

### **3. Instalación de Dependencias**
```bash
pip install -r requirements.txt
```

## 🧪 **Plan de Testing Detallado**

### **FASE 1: Verificación de Infraestructura**

#### **1.1 Iniciar Aplicación Local**
```bash
# Desde el directorio del proyecto
python start.py
```

**Verificaciones:**
- [ ] La aplicación inicia sin errores
- [ ] Se ejecuta la migración automática de base de datos
- [ ] Se crean las tablas necesarias (especialmente `daemon_status`)
- [ ] El daemon de reservas automáticas se inicia correctamente
- [ ] Los logs muestran `[RESERVAS-DAEMON] Daemon iniciado`
- [ ] Los logs muestran `[DAEMON-MONITOR] Sistema de monitoreo inicializado`

#### **1.2 Verificar Acceso Web**
- [ ] Acceder a `http://localhost:5000`
- [ ] Login funciona correctamente
- [ ] Dashboard principal carga sin errores

### **FASE 2: Testing del Sistema de Reservas Automáticas**

#### **2.1 Verificar Campos en Base de Datos**
```sql
-- Verificar que los nuevos campos existen en la tabla leads
DESCRIBE leads;

-- Verificar campos específicos
SELECT 
    reserva_automatica, 
    preferencia_horario, 
    fecha_minima_reserva 
FROM leads 
LIMIT 5;
```

#### **2.2 Testing de API de Actualización**
**Test 1: Marcar lead para reserva automática**
```bash
curl -X POST http://localhost:5000/api/actualizar_resultado \
  -H "Content-Type: application/json" \
  -d '{
    "telefono": "+34600123456",
    "reservaAutomatica": true,
    "preferenciaHorario": "mañana",
    "fechaMinimaReserva": "25/07/2024"
  }'
```

**Verificaciones:**
- [ ] Respuesta HTTP 200
- [ ] Campo `reserva_automatica` = TRUE en BD
- [ ] Campo `preferencia_horario` = 'mañana'
- [ ] Campo `fecha_minima_reserva` correctamente parseado

**Test 2: Consultar leads marcados**
```bash
curl http://localhost:5000/api/leads_reserva_automatica
```

**Verificaciones:**
- [ ] Devuelve leads marcados para reserva automática
- [ ] JSON bien formado con todos los campos

### **FASE 3: Testing del Sistema de Monitoreo del Daemon**

#### **3.1 Verificar APIs de Monitoreo**

**Test 1: Estado del daemon**
```bash
curl http://localhost:5000/api/daemon/status
```

**Verificaciones:**
- [ ] Respuesta HTTP 200
- [ ] Campo `daemon_running` = true
- [ ] Campo `last_heartbeat` con timestamp reciente
- [ ] Estructura JSON correcta

**Test 2: Healthcheck**
```bash
curl http://localhost:5000/api/daemon/healthcheck
```

**Verificaciones:**
- [ ] Respuesta HTTP 200 si daemon saludable
- [ ] Respuesta HTTP 503 si daemon no saludable
- [ ] Mensaje descriptivo del estado

**Test 3: Estadísticas**
```bash
curl http://localhost:5000/api/daemon/stats
```

**Verificaciones:**
- [ ] Estadísticas de leads procesados
- [ ] Contadores de reservas exitosas/fallidas
- [ ] Tasa de éxito calculada correctamente

**Test 4: Alertas**
```bash
curl http://localhost:5000/api/daemon/alert
```

**Verificaciones:**
- [ ] Detección de alertas críticas
- [ ] Clasificación por severidad
- [ ] Mensajes descriptivos

#### **3.2 Testing del Dashboard de Monitoreo**

**Acceder a:** `http://localhost:5000/daemon/status`

**Verificaciones:**
- [ ] Página carga sin errores JavaScript
- [ ] Indicador de heartbeat se muestra correctamente
- [ ] Estado del daemon se actualiza automáticamente
- [ ] Estadísticas se muestran correctamente
- [ ] Alertas aparecen si las hay
- [ ] Botón de actualización funciona
- [ ] Actualización automática cada 30 segundos

### **FASE 4: Testing del Sistema de Verificación Railway**

#### **4.1 Verificar APIs de Verificación**

**Test 1: Configuración**
```bash
curl http://localhost:5000/api/railway/config
```

**Verificaciones:**
- [ ] URL base configurada correctamente
- [ ] Lista de endpoints a verificar
- [ ] Configuración de timeout

**Test 2: Verificación rápida**
```bash
curl http://localhost:5000/api/railway/quick-check
```

**Verificaciones:**
- [ ] Verifica servicios principales
- [ ] Calcula estadísticas correctamente
- [ ] Tiempos de respuesta incluidos

**Test 3: Iniciar verificación completa**
```bash
curl -X POST http://localhost:5000/api/railway/verify
```

**Verificaciones:**
- [ ] Respuesta HTTP 202 (Accepted)
- [ ] Mensaje de verificación iniciada

**Test 4: Estado de verificación**
```bash
curl http://localhost:5000/api/railway/status
```

**Verificaciones:**
- [ ] Progreso de verificación
- [ ] Estado actual del test
- [ ] Indicador de ejecución

**Test 5: Resultados**
```bash
curl http://localhost:5000/api/railway/results
```

**Verificaciones:**
- [ ] Resultados detallados por servicio
- [ ] Resumen con estadísticas
- [ ] Clasificación de estado general

#### **4.2 Testing del Dashboard de Verificación**

**Acceder a:** `http://localhost:5000/admin/railway-verification`

**Verificaciones:**
- [ ] Página carga sin errores
- [ ] Verificación rápida funciona
- [ ] Verificación completa se ejecuta
- [ ] Barra de progreso se actualiza
- [ ] Resultados se muestran correctamente
- [ ] Estados se colorean apropiadamente
- [ ] Tiempos de respuesta se muestran

### **FASE 5: Testing de Integración**

#### **5.1 Acceso desde Herramientas de Admin**

**Acceder a:** `http://localhost:5000/admin/tools`

**Verificaciones:**
- [ ] Tarjeta "Reservas Automáticas" visible
- [ ] Enlace al dashboard del daemon funciona
- [ ] Tarjeta "Verificación Railway" visible
- [ ] Enlace al dashboard de verificación funciona

#### **5.2 Testing del Procesador de Reservas**

**Esperar 1-2 minutos (intervalo configurado) y verificar:**
- [ ] Logs muestran `[RESERVAS-DAEMON] --- Iniciando ciclo`
- [ ] Se procesan leads marcados para reserva automática
- [ ] Se actualizan estadísticas en el monitor
- [ ] Se registra heartbeat en base de datos

**Verificar en BD:**
```sql
SELECT * FROM daemon_status WHERE daemon_name = 'reservas_automaticas';
```

### **FASE 6: Testing de Casos de Error**

#### **6.1 Simular Daemon Detenido**
- [ ] Detener manualmente el daemon
- [ ] Verificar que healthcheck devuelve 503
- [ ] Verificar alertas críticas en dashboard
- [ ] Verificar indicador rojo en interfaz

#### **6.2 Simular Errores de API**
- [ ] Configurar credenciales TuoTempo incorrectas
- [ ] Verificar manejo de errores en procesador
- [ ] Verificar registro de errores en monitor
- [ ] Verificar alertas de advertencia

#### **6.3 Simular Problemas de BD**
- [ ] Desconectar temporalmente MySQL
- [ ] Verificar manejo de errores de conexión
- [ ] Verificar logs de error apropiados

## 📊 **Checklist de Validación Final**

### **Funcionalidad Core**
- [ ] Leads se pueden marcar para reserva automática
- [ ] API acepta todos los parámetros nuevos
- [ ] Daemon procesa leads automáticamente
- [ ] Reservas se realizan correctamente (mock)

### **Monitoreo**
- [ ] Heartbeat se actualiza regularmente
- [ ] Estadísticas se registran correctamente
- [ ] Alertas se generan apropiadamente
- [ ] Dashboard muestra información en tiempo real

### **Verificación Railway**
- [ ] Todos los endpoints se verifican
- [ ] Resultados son precisos
- [ ] Dashboard es funcional e intuitivo
- [ ] Ejecución asíncrona funciona

### **Integración**
- [ ] Todas las APIs están registradas
- [ ] Rutas web funcionan correctamente
- [ ] Acceso desde admin tools funciona
- [ ] No hay errores JavaScript en consola

### **Rendimiento**
- [ ] Páginas cargan en < 3 segundos
- [ ] APIs responden en < 1 segundo
- [ ] Verificación completa termina en < 2 minutos
- [ ] No hay memory leaks evidentes

## 🚨 **Criterios de Éxito**

**Para proceder al despliegue, TODOS los siguientes deben cumplirse:**

1. ✅ **Sin errores críticos**: No hay errores 500 o crashes
2. ✅ **Funcionalidad completa**: Todas las features funcionan como se espera
3. ✅ **Monitoreo operativo**: Dashboards muestran datos correctos
4. ✅ **APIs estables**: Todos los endpoints responden apropiadamente
5. ✅ **Logs limpios**: No hay errores repetitivos en logs
6. ✅ **Base de datos consistente**: Migraciones y datos correctos
7. ✅ **Interfaz funcional**: Sin errores JavaScript críticos

## 📝 **Documentación de Resultados**

**Crear archivo `TESTING_RESULTS.md` con:**
- Fecha y hora de testing
- Versión testeada
- Resultados de cada fase
- Issues encontrados y resoluciones
- Screenshots de dashboards funcionando
- Logs relevantes
- Recomendaciones para despliegue

---

**¡Una vez completado este plan, el sistema estará listo para despliegue en Railway con confianza total!** 🚀

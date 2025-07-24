# Despliegue de Reservas Automáticas en Railway

Esta guía explica cómo configurar y desplegar el sistema de reservas automáticas en Railway.

## 🚀 Configuración en Railway

### 1. Variables de Entorno Requeridas

Asegúrate de que estas variables estén configuradas en tu proyecto de Railway:

#### Base de Datos (ya existentes):
```
MYSQLHOST=containers-us-west-xxx.railway.app
MYSQLUSER=root
MYSQLPASSWORD=tu_password
MYSQLDATABASE=railway
MYSQLPORT=3306
```

#### API de TuoTempo (nuevas - REQUERIDAS):
```
TUOTEMPO_API_BASE_URL=https://api.tuotempo.com/v1
TUOTEMPO_API_TOKEN=tu_token_de_api
```

#### Configuración del Daemon (opcionales):
```
RESERVAS_INTERVAL_MINUTES=30          # Intervalo en minutos (default: 30)
RESERVAS_MODE=daemon                  # 'daemon' o 'single' (default: daemon)
RUN_MIGRATION=true                    # Ejecutar migración automática (default: true)
```

### 2. Servicios en Railway

Tienes dos opciones para desplegar el sistema:

#### Opción A: Servicio Separado (RECOMENDADO)

1. **Crear nuevo servicio** en Railway llamado `reservas-automaticas`
2. **Configurar variables de entorno** (las mismas que el servicio principal)
3. **Establecer comando de inicio**:
   ```
   python railway_reservas_setup.py
   ```

#### Opción B: Integrado en el Servicio Principal

Modificar el archivo `start.py` para incluir el daemon como hilo en segundo plano.

### 3. Migración Automática

La migración de base de datos se ejecuta automáticamente:

1. **El sistema existente** (`db_schema_manager.py`) lee `schema.sql`
2. **Detecta automáticamente** los nuevos campos de reservas automáticas
3. **Aplica las modificaciones** sin intervención manual
4. **Crea índices** para optimizar consultas

#### Campos que se añaden automáticamente:
- `reserva_automatica` (BOOLEAN, default FALSE)
- `preferencia_horario` (ENUM('mañana', 'tarde'), default 'mañana')
- `fecha_minima_reserva` (DATE, NULL)

## 🔧 Configuración Paso a Paso

### Paso 1: Preparar Variables de Entorno

En el dashboard de Railway, ve a tu proyecto y añade estas variables:

```bash
# Variables nuevas requeridas
TUOTEMPO_API_BASE_URL=https://api.tuotempo.com/v1
TUOTEMPO_API_TOKEN=tu_token_aqui

# Variables opcionales
RESERVAS_INTERVAL_MINUTES=30
RESERVAS_MODE=daemon
```

### Paso 2: Crear Servicio de Reservas (Opción A)

1. En Railway, crea un **nuevo servicio**
2. **Conecta el mismo repositorio**
3. **Nombre del servicio**: `reservas-automaticas`
4. **Comando de inicio**: `python railway_reservas_setup.py`
5. **Variables de entorno**: Copia todas las variables del servicio principal

### Paso 3: Verificar Despliegue

El servicio mostrará logs como estos si todo está correcto:

```
🚀 Iniciando sistema de reservas automáticas en Railway
=== Verificando configuración de entorno ===
✅ Variable configurada: MYSQLHOST
✅ Variable configurada: TUOTEMPO_API_BASE_URL
=== Ejecutando migración de base de datos ===
✅ Migración de base de datos completada exitosamente
=== Probando conexión a base de datos ===
✅ Todos los campos de reservas automáticas están disponibles
✅ Encontrados 0 leads marcados para reserva automática
=== Iniciando daemon de reservas automáticas ===
🚀 Daemon de reservas automáticas iniciado
Intervalo configurado: 30 minutos
```

## 📊 Monitoreo y Logs

### Logs del Sistema

El daemon genera logs detallados:

```
--- Iniciando ciclo de procesamiento: 2024-07-24 17:30:00 ---
Encontrados 5 leads marcados para reserva automática
Procesando lead 123: Juan Pérez
Encontrados 3 slots disponibles para area_456 (mañana)
Reserva realizada exitosamente para lead 123
--- Ciclo completado en 45.32 segundos ---
⏰ Esperando 30 minutos hasta el próximo procesamiento...
```

### Métricas Importantes

- **Leads procesados por ciclo**
- **Reservas exitosas vs fallidas**
- **Tiempo de procesamiento por ciclo**
- **Errores de conexión a APIs**

## 🛠️ Troubleshooting

### Error: Variables de entorno faltantes
```
❌ Variable de entorno faltante: TUOTEMPO_API_TOKEN
```
**Solución**: Configurar la variable en Railway dashboard

### Error: Migración falló
```
❌ La migración de base de datos falló
```
**Solución**: Verificar conexión a MySQL y permisos

### Error: No se pueden realizar reservas
```
❌ Error al realizar reserva para lead 123: 401 - Unauthorized
```
**Solución**: Verificar `TUOTEMPO_API_TOKEN` y permisos de API

### Error: Conexión a base de datos
```
❌ No se pudo conectar a la base de datos
```
**Solución**: Verificar variables `MYSQL*` y estado del servicio MySQL

## 🔄 Mantenimiento

### Reiniciar el Daemon

En Railway dashboard:
1. Ve al servicio `reservas-automaticas`
2. Click en "Restart"
3. Monitorea los logs para verificar que inicia correctamente

### Cambiar Intervalo de Procesamiento

1. Modifica `RESERVAS_INTERVAL_MINUTES` en Railway
2. Reinicia el servicio
3. El nuevo intervalo se aplicará automáticamente

### Ejecutar Procesamiento Manual

Para ejecutar una sola vez (testing):
1. Establece `RESERVAS_MODE=single`
2. Reinicia el servicio
3. El servicio procesará una vez y se detendrá

## 📈 Escalabilidad

### Múltiples Instancias

- **NO ejecutar múltiples instancias** del daemon simultáneamente
- Puede causar reservas duplicadas
- Railway maneja automáticamente la disponibilidad del servicio

### Optimización

- El sistema procesa hasta **100 leads por ciclo**
- Pausa de **2 segundos** entre reservas para no sobrecargar APIs
- **Índices optimizados** en base de datos para consultas rápidas

## 🔐 Seguridad

### Tokens de API

- Nunca hardcodear tokens en el código
- Usar variables de entorno de Railway
- Rotar tokens periódicamente

### Acceso a Base de Datos

- Usar las mismas credenciales que el servicio principal
- Railway maneja automáticamente la seguridad de red

## 📞 Soporte

Si encuentras problemas:

1. **Revisa los logs** en Railway dashboard
2. **Verifica variables de entorno**
3. **Comprueba estado de servicios** (MySQL, API TuoTempo)
4. **Consulta esta documentación**

El sistema está diseñado para ser robusto y auto-recuperarse de errores temporales.

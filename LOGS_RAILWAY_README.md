# Logs de APIs de Tuotempo en Railway

Este documento explica cómo funciona el sistema de logging de las APIs de tuotempo cuando la aplicación está desplegada en Railway.

## ¿Dónde están los logs en Railway?

En Railway, los logs se almacenan en **dos lugares diferentes**:

### 1. Logs de Aplicación de Railway (Principales)
- **Ubicación**: Panel de Railway > Tu Proyecto > Logs
- **Formato**: Los logs aparecen con el prefijo `[TUOTEMPO_API]`
- **Acceso**: A través del dashboard web de Railway
- **Persistencia**: Railway mantiene los logs por un tiempo limitado

### 2. Archivo de Log Temporal
- **Ubicación**: `/tmp/tuotempo_api_calls.log` dentro del contenedor
- **Formato**: JSON estructurado
- **Acceso**: A través del endpoint `/api/logs/tuotempo`
- **Persistencia**: Se pierde cuando el contenedor se reinicia

## Cómo Acceder a los Logs

### Método 1: Panel de Railway
1. Ve a https://railway.app/dashboard
2. Selecciona tu proyecto
3. Ve a la pestaña "Logs"
4. Busca entradas que contengan `[TUOTEMPO_API]`

### Método 2: Endpoint de API
```bash
curl "https://tu-app.railway.app/api/logs/tuotempo?max_lines=20&hours_ago=1"
```

Parámetros:
- `max_lines`: Número máximo de líneas (default: 50)
- `hours_ago`: Filtrar logs de las últimas X horas (default: 24)

### Método 3: Script de Python
```python
python acceder_logs_railway.py https://tu-app.railway.app
```

## Formato de los Logs

Cada entrada de log contiene:

```json
{
  "timestamp": "2024-12-25T10:30:00.123456",
  "method": "GET",
  "endpoint": "https://app.tuotempo.com/api/v3/tt_portal_adeslas/availabilities",
  "params": {
    "activityid": "sc159232371eb9c1",
    "areaId": "44kowswy",
    "start_date": "25/12/2024"
  },
  "payload": {},
  "response": {
    "result": "OK",
    "availabilities": [...]
  },
  "error": null,
  "success": true
}
```

## Qué se Registra Automáticamente

### APIs de TuoTempoAPI
- ✅ `get_centers()` - Obtener centros
- ✅ `get_available_slots()` - Obtener slots disponibles
- ✅ `register_non_insured_user()` - Registrar usuario
- ✅ `confirm_appointment()` - Confirmar cita
- ✅ `cancel_appointment()` - Cancelar cita

### Clase Tuotempo (Adaptador)
- ✅ `get_available_slots()` - Obtener slots
- ✅ `create_reservation()` - Crear reserva

### Llamadas HTTP
- ✅ Todas las llamadas requests.get/post/delete
- ✅ URLs, parámetros, payloads y respuestas
- ✅ Códigos de estado y errores

## Monitoreo en Tiempo Real

### Usando Railway CLI
```bash
railway logs --follow
```

Filtra por logs de tuotempo:
```bash
railway logs --follow | grep "TUOTEMPO_API"
```

### Usando el Script de Monitoreo
```python
python acceder_logs_railway.py https://tu-app.railway.app
# Seleccionar opción de monitoreo continuo
```

## Ejemplos de Uso

### Ver Logs de las Últimas 2 Horas
```bash
curl "https://tu-app.railway.app/api/logs/tuotempo?hours_ago=2" | jq .
```

### Contar Llamadas Exitosas/Fallidas
```python
import requests

response = requests.get("https://tu-app.railway.app/api/logs/tuotempo")
logs = response.json()['logs']

exitosas = sum(1 for log in logs if log.get('success'))
fallidas = sum(1 for log in logs if not log.get('success'))

print(f"Exitosas: {exitosas}, Fallidas: {fallidas}")
```

### Buscar Errores Específicos
```python
response = requests.get("https://tu-app.railway.app/api/logs/tuotempo")
logs = response.json()['logs']

errores = [log for log in logs if log.get('error')]
for error in errores:
    print(f"Error: {error['error']}")
```

## Consideraciones Importantes

### Persistencia
- **Railway Logs**: Se mantienen por tiempo limitado (días/semanas)
- **Archivo /tmp**: Se pierde al reiniciar el contenedor
- **Recomendación**: Exportar logs importantes regularmente

### Rendimiento
- Los logs no afectan significativamente el rendimiento
- Se escriben de forma asíncrona
- El endpoint `/api/logs/tuotempo` es rápido para consultas pequeñas

### Privacidad
- Los logs pueden contener información sensible
- No se registran credenciales o passwords
- Los datos de usuarios se registran para debugging

### Límites
- El archivo temporal tiene un tamaño máximo (no rotación automática)
- Railway tiene límites en la retención de logs
- El endpoint de logs puede devolver máximo 1000 entradas

## Troubleshooting

### "No se encontraron logs"
- Verifica que la aplicación esté recibiendo tráfico
- Comprueba que las APIs de tuotempo se estén llamando
- Revisa los logs generales de Railway por errores

### "Error al obtener logs via API"
- Verifica que la URL de Railway sea correcta
- Comprueba que el endpoint esté funcionando: `/api/status`
- Revisa los logs de Railway por errores de la aplicación

### "Logs muy antiguos"
- Railway rota los logs automáticamente
- Usa `hours_ago=24` para obtener logs más recientes
- Considera implementar exportación automática de logs

## Scripts Útiles

### Exportar Logs a Archivo
```python
import requests
import json
from datetime import datetime

response = requests.get("https://tu-app.railway.app/api/logs/tuotempo")
logs = response.json()['logs']

filename = f"tuotempo_logs_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(filename, 'w') as f:
    json.dump(logs, f, indent=2)

print(f"Logs exportados a {filename}")
```

### Alertas por Errores
```python
import requests
import time

def check_errors():
    response = requests.get("https://tu-app.railway.app/api/logs/tuotempo?hours_ago=1")
    logs = response.json()['logs']

    errors = [log for log in logs if log.get('error')]
    if errors:
        print(f"¡ALERTA! {len(errors)} errores encontrados:")
        for error in errors[-3:]:  # Últimos 3 errores
            print(f"- {error['timestamp']}: {error['error']}")

# Ejecutar cada 5 minutos
while True:
    check_errors()
    time.sleep(300)
```

## Conclusión

El sistema de logging está diseñado para funcionar tanto en local como en Railway, proporcionando visibilidad completa de todas las llamadas a las APIs de tuotempo. Los logs están disponibles tanto en el panel de Railway como a través de endpoints de API, permitiendo monitoreo en tiempo real y análisis post-mortem.
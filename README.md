# TuoTempo - Sistema de Gestión de Contactos

Este proyecto es una aplicación web basada en Flask para la gestión de contactos y resultados de llamadas. Incluye un panel de administración y varias APIs REST para la integración con otros sistemas.

## Características principales

- **Panel de administración** con autenticación segura
- **Carga de datos** desde archivos Excel
- **Exportación de datos** a Excel
- **APIs REST** para consulta de centros, actividades, slots y actualización de resultados de llamadas
- **Historial de recargas** de datos

## URLs de las APIs desplegadas

### API de Resultado de Llamadas
- **URL Base**: https://actualizarllamadas-production.up.railway.app
- **Endpoints**:
  - `GET /api/status` - Verifica el estado de la API
  - `POST /api/actualizar_resultado` - Actualiza el resultado de una llamada

### API de TuoTempo (pendiente de desplegar)
- **URL Base**: [Pendiente de despliegue]
- **Endpoints**:
  - `GET /api/status` - Verifica el estado de la API
  - `GET /api/centros` - Obtiene centros con filtros opcionales
  - `GET /api/centros?cp=XXXXX` - Filtra centros por código postal
  - `GET /api/centros?provincia=XXXXX` - Filtra centros por provincia
  - `GET /api/centros/XXXXX` - Obtiene centros por código postal (versión REST)
  - `GET /api/actividades?centro_id=XXXXX` - Obtiene actividades disponibles en un centro
  - `GET /api/slots?centro_id=XXX&actividad_id=YYY&fecha_inicio=DD/MM/YYYY` - Obtiene slots disponibles

## Documentación de la API

### Endpoint: POST /api/actualizar_resultado
Servicio para actualizar el estado de un lead después de una llamada.

**Parámetros JSON**  
Los campos `status_level_1` y `status_level_2` **ya no se envían**; el backend los calcula automáticamente a partir de las reglas de negocio.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `telefono` | string | Sí | Número de teléfono del lead. |
| `nuevaCita` | string `YYYY-MM-DD HH:MM` | No | Si se informa, la llamada se marca como **Éxito / Cita programada**. |
| `buzon` | boolean | No | `true` si la llamada cae en buzón ⇒ **Volver a llamar / buzón**. |
| `volverALlamar` | boolean | No | `true` para indicar que se debe volver a llamar. |
| `noInteresado` | boolean | No | `true` ⇒ **No Interesado**. |
| `conPack` | boolean | No | `true` ⇒ **Éxito / Contratado**. |
| `horaRellamada` | string `HH:MM` | No | Hora sugerida para la rellamada. |
| `errorTecnico` | boolean | No | `true` ⇒ **Volver a llamar / Problema técnico**. |
| `razonvueltaallamar` | string | No | Motivo textual de la rellamada. |
| `razonNoInteres` | string | No | Motivo textual de no interés. |
| `codigoNoInteres` | string | No | Código corto para no interés (`no disponibilidad`, `descontento`, `bajaProxima`, `otros`). |
| `codigoVolverLlamar` | string | No | Código corto para rellamada (`buzon`, `interrupcion`, `proble_tecnico`). |

*Debe enviarse al menos un campo opcional (además de `telefono`) para que la petición sea procesada.*

**Respuestas**
| Código | Caso |
|--------|------|
| `200` | Actualización correcta. Devuelve `{ "success": true, "message": "..." }` |
| `400` | Faltan datos obligatorios (`telefono`) o no se proporciona ningún campo para actualizar. |
| `404` | No existe lead con el teléfono indicado. |
| `500` | Error de base de datos.

Ejemplo completo:
```bash
curl -X POST https://actualizarllamadas-production.up.railway.app/api/actualizar_resultado \
  -H "Content-Type: application/json" \
  -d '{
    "telefono": "600123456",
    "nuevaCita": "2025-08-01 10:00",
    "buzon": false,
    "volverALlamar": false,
    "noInteresado": false,
    "conPack": true,
    "horaRellamada": "18:30",
    "errorTecnico": false,
    "razonvueltaallamar": "Cliente ocupado",
    "razonNoInteres": "No le interesa el producto",
    "codigoNoInteres": "descontento",
    "codigoVolverLlamar": "buzon"
  }'
```

Para más detalles ver `API_DOCUMENTATION.md`.


La documentación completa de la API de resultados de llamadas está disponible en el archivo [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

Adicionalmente, la documentación de la API de TuoTempo está disponible en [https://apidoc.tuotempo.com/](https://apidoc.tuotempo.com/), donde también hay una interfaz web para lanzar peticiones de prueba y revisar entradas y salidas de datos.

## Requisitos

- Python 3.6+
- Paquetes requeridos en `requirements.txt`

## Instalación

1. Clonar el repositorio
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear un archivo `.env` basado en `.env.example` e indicar al menos:

```text
SECRET_KEY=<valor seguro para Flask>
MYSQL_HOST=<host MySQL>
MYSQL_USER=<usuario MySQL>
MYSQL_PASSWORD=<contraseña MySQL>
MYSQL_DATABASE=<nombre BD>
MYSQL_PORT=<puerto MySQL>
TUOTEMPO_INSTANCE_ID=tt_portal_adeslas
```

## Gestión de la Base de Datos y Migraciones

Este proyecto utiliza un **sistema de migración de base de datos inteligente y automatizado** para mantener el esquema de la base de datos sincronizado con el código.

### ¿Cómo funciona?

1.  **Fuente Única de Verdad**: El fichero `schema.sql` es la **definición canónica** de la estructura de la base de datos. Contiene todas las sentencias `CREATE TABLE` que describen el estado ideal del esquema.
2.  **Gestor de Esquemas Automático**: El script `db_schema_manager.py` es el encargado de las migraciones. **No es necesario ejecutarlo manualmente**.
3.  **Ejecución en el Arranque**: El orquestador principal (`start.py`) ejecuta este gestor de esquemas cada vez que la aplicación se inicia (tanto en local como en producción).
4.  **Comparación y Aplicación**: El gestor compara el esquema definido en `schema.sql` con el esquema de la base de datos activa. Si detecta discrepancias (tablas o columnas que faltan), genera y ejecuta automáticamente las sentencias `CREATE TABLE` o `ALTER TABLE` necesarias para sincronizar la base de datos.

### Flujo de trabajo para desarrolladores

Si necesitas realizar un cambio en la estructura de la base de datos (añadir una tabla, una columna, etc.), el proceso es muy sencillo:

1.  **Modifica `schema.sql`**: Abre el fichero `schema.sql` y aplica los cambios directamente en la sentencia `CREATE TABLE` correspondiente.
2.  **Reinicia la aplicación**: La próxima vez que la aplicación se inicie, el sistema de migración detectará tus cambios y los aplicará a la base de datos automáticamente.

**Ya no es necesario crear scripts de migración manuales (`db_migration_*.py`).**

## Flujo de integración

El flujo implementado sigue estos pasos:

1. **Obtener centros**: Acotar los centros para los que se realizará la búsqueda
2. **Obtener huecos**: Buscar huecos en los centros identificados
3. **Registrar no asegurado**: Crear la ficha del receptor de la cita
4. **Confirmar cita**: Crear una cita asociada a la ficha de receptor de la cita creada en el paso anterior

## Uso

El archivo `example.py` contiene un ejemplo completo de uso de la API. Para ejecutarlo:

```bash
python example.py
```

## Clase TuoTempoAPI

La clase `TuoTempoAPI` en `tuotempo_api.py` proporciona métodos para interactuar con la API de TuoTempo:

- `get_centers()`: Obtiene el listado de centros
- `get_available_slots()`: Obtiene huecos disponibles
- `register_non_insured_user()`: Registra un usuario no asegurado
- `confirm_appointment()`: Confirma una cita
- `handle_error()`: Maneja errores de la API

## Ejemplo de uso

```python
from tuotempo_api import TuoTempoAPI

# Inicializar cliente
api = TuoTempoAPI(lang="es")

# Obtener centros
centers = api.get_centers()

# Obtener huecos disponibles
slots = api.get_available_slots(
    activity_id="sc159232371eb9c1",  # Primera visita odontología general
    area_id="default@tt_adeslas_ecexpd4f_ef3ewl7a_ei4z3vee_44xewswy_sejh",
    start_date="20/06/2025"
)

# Registrar usuario no asegurado
user = api.register_non_insured_user(
    fname="Juan",
    lname="Pérez",
    birthday="01/01/1980",
    phone="600123456"
)

# Confirmar cita
appointment = api.confirm_appointment(
    availability=slots["return"]["results"]["availabilities"][0],
    communication_phone="600123456"
)
```

## Gestión de errores

La API maneja los siguientes casos de error:

- `TUOTEMPO_RESOURCE_NOT_ALLOWED`: No se han encontrado huecos para los criterios indicados
- `TUOTEMPO_MAX_RES_BOOKED_ONLINE`: El usuario tiene ya otra cita para el mismo día
- `PROVIDER_RESERVATION_CONFLICT_ERROR` / `MEMBER_RESERVATION_CONFLICT_ERROR`: El hueco ha sido agendado por otro usuario

## Notas importantes

- Para todas las llamadas el campo "instance_id" debe informarse con el valor "tt_portal_adeslas" en caso de producción.
- Para todas las llamadas, el header siempre tendrá informado como mínimo el campo "content-type" con el valor "application/json; charset=UTF-8"
- Para todas las llamadas el query string deberá contener el campo lang informado según el idioma para atender al usuario: "es" (castellano), "en" (inglés), "ca" (catalán)

## Opciones de despliegue

### 1. Como script Python

Para ejecutar el script periódicamente o bajo demanda:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar el script
python example.py
```

### 2. Como API web

Se ha incluido un archivo `app.py` que expone la funcionalidad como una API web usando Flask:

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en desarrollo
python app.py

# Ejecutar en producción con gunicorn (Linux/Mac)
gunicorn app:app --bind 0.0.0.0:5000

# Ejecutar en producción con waitress (Windows)
pip install waitress
waitress-serve --port=5000 app:app
```

#### Endpoints disponibles

- `GET /health` - Comprueba si el servicio está funcionando
- `GET /centers?province=Madrid` - Obtiene centros filtrados por provincia
- `GET /slots?area_id=XXX&start_date=DD/MM/YYYY` - Obtiene huecos disponibles
- `POST /register` - Registra un usuario no asegurado
- `POST /confirm` - Confirma una cita
- `GET /api/clinica/code?q=<texto>` - Devuelve el código de clínicas cuyo nombre o dirección contenga `<texto>`
- `GET /api/clinica/code?q=<texto>&campo=<nombre|direccion>` - Busca el código de hasta **3** clínicas por nombre o por dirección.

  - Parámetros:
    - `q` : fragmento de texto a buscar
    - `campo`: `nombre` o `direccion`

### 3. Despliegue en la nube

Para desplegar en servicios cloud:

#### Railway

```bash
# Instalar CLI de Railway e iniciar sesión
railway login

# Crear proyecto y servicio MySQL en Railway
railway init
railway addon create mysql

# Configurar variables de entorno (Environment Variables) en el panel de Railway:
# SECRET_KEY, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_PORT

# Desplegar al repositorio remoto
git push railway main

### Carga de datos desde Excel

Railway expone un endpoint para importar el Excel en la BD:

```bash
curl https://<TU_APP_RAILWAY>.up.railway.app/admin/load-excel
```

Este endpoint descargará el archivo definido en `EXCEL_URL` (GitHub raw) y lo volcará en la tabla `leads`.
Alternativamente, para correrlo desde la CLI de Railway:

```bash
railway run python railway_import_data.py https://raw.githubusercontent.com/jbenoliel/tuotempo/main/data.xlsx
```

#### Heroku

```bash
# Instalar CLI de Heroku
# Iniciar sesión
heroku login

# Crear aplicación
heroku create tuotempo-integration

# Desplegar
git push heroku main
```

#### Azure App Service

```bash
# Instalar Azure CLI
az login
az webapp up --runtime PYTHON:3.9 --sku B1 --name tuotempo-integration
```

#### AWS Elastic Beanstalk

```bash
# Instalar EB CLI
pip install awsebcli

# Inicializar
eb init -p python-3.9 tuotempo-integration

# Crear entorno y desplegar
eb create tuotempo-integration-env
```

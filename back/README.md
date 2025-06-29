# TuoTempo API Integration

Este proyecto es una integración con las APIs de TuoTempo para realizar el proceso de citación médica.

## Documentación

La documentación completa de todos los métodos está disponible en [https://apidoc.tuotempo.com/](https://apidoc.tuotempo.com/), donde también hay una interfaz web para lanzar peticiones de prueba y revisar entradas y salidas de datos.

## Requisitos

- Python 3.6+
- Paquetes requeridos en `requirements.txt`

## Instalación

1. Clonar el repositorio
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. (Opcional) Crear un archivo `.env` con la siguiente configuración:

```
TUOTEMPO_INSTANCE_ID=tt_portal_adeslas
```

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

### 3. Despliegue en la nube

Para desplegar en servicios cloud:

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

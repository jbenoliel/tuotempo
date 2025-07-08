# API de Saludo

Una API simple que devuelve un saludo dependiendo de la hora del día.

## Endpoints

### `/api/saludo`
Devuelve un saludo basado en la hora actual:
- "Buenos días" si es antes de las 14:00
- "Buenas tardes" si es después de las 14:00

Ejemplo de respuesta:
```json
{
  "mensaje": "Buenos días",
  "hora": 10,
  "timestamp": "2025-07-08 10:21:35"
}
```

### `/health`
Endpoint para verificar que la API está funcionando correctamente.

## Instrucciones de despliegue en Railway

1. Crea una cuenta en [Railway](https://railway.app/) si aún no tienes una
2. Instala la CLI de Railway (opcional):
   ```bash
   npm i -g @railway/cli
   ```
3. Inicia sesión en Railway:
   ```bash
   railway login
   ```
4. Crea un nuevo proyecto en Railway:
   ```bash
   railway init
   ```
5. Despliega la aplicación:
   ```bash
   railway up
   ```

Alternativamente, puedes conectar tu repositorio de GitHub directamente desde el dashboard de Railway.

## Desarrollo local

Para ejecutar la API localmente:

```bash
pip install -r requirements-saludo.txt
python saludo_api.py
```

La API estará disponible en http://localhost:5000

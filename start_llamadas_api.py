from flask import Flask
from api_resultado_llamada import resultado_api

app = Flask(__name__)

# Registrar solo el blueprint de la API de resultados de llamadas
app.register_blueprint(resultado_api)

if __name__ == '__main__':
    # Esto es para pruebas locales, Railway usará Gunicorn directamente
    app.run(host='0.0.0.0', port=5003, debug=True)

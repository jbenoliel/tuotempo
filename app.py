# Este archivo es un puente para Railway
# Importa y expone la app Flask desde app_dashboard.py

from app_dashboard import app

# No es necesario nada más, este archivo solo sirve para exponer la app
# para que Railway pueda encontrarla incluso si sigue ignorando el Procfile

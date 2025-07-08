#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, jsonify
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/api/saludo', methods=['GET'])
def saludo():
    """
    Endpoint que responde con un saludo según la hora del día:
    - Buenos días: si es antes de las 14h
    - Buenas tardes: si es después de las 14h
    """
    hora_actual = datetime.now().hour
    
    if hora_actual < 14:
        mensaje = "Buenos días"
    else:
        mensaje = "Buenas tardes"
    
    return jsonify({
        "mensaje": mensaje,
        "hora": hora_actual,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "ok",
        "version": "1.0.0"
    })

@app.route('/', methods=['GET'])
def root():
    """Página principal con instrucciones"""
    return """
    <html>
        <head>
            <title>API de Saludo</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                }
                code {
                    background-color: #f4f4f4;
                    padding: 2px 5px;
                    border-radius: 4px;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>API de Saludo</h1>
                <p>Esta API responde con un saludo según la hora del día.</p>
                
                <h2>Endpoints disponibles:</h2>
                <ul>
                    <li><code>/api/saludo</code> - Devuelve "Buenos días" si es antes de las 14h, o "Buenas tardes" si es después.</li>
                    <li><code>/health</code> - Verifica que la API está funcionando.</li>
                </ul>
                
                <h2>Ejemplo de respuesta:</h2>
                <pre>
                {
                    "mensaje": "Buenos días",
                    "hora": 10,
                    "timestamp": "2025-07-08 10:21:35"
                }
                </pre>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    # Obtener puerto del entorno o usar 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    
    # Ejecutar la aplicación
    app.run(host='0.0.0.0', port=port, debug=True)

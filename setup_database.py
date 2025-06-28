from flask import Flask, render_template, redirect, url_for, request, flash
import os
from create_mysql_database import main as setup_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_temporal')

@app.route('/')
def index():
    return render_template('setup_db.html')

@app.route('/setup_database', methods=['POST'])
def setup_database():
    try:
        # Ejecutar la configuración de la base de datos
        setup_db()
        flash('Base de datos configurada correctamente', 'success')
    except Exception as e:
        flash(f'Error al configurar la base de datos: {str(e)}', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

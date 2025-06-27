from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "segurcaixa_dashboard_secret_key"

# Configuración de la base de datos
DB_CONFIG = {
    'host': os.environ.get('MYSQLHOST') or os.environ.get('MYSQL_HOST', 'localhost'),
    'user': os.environ.get('MYSQLUSER') or os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQLPASSWORD') or os.environ.get('MYSQL_PASSWORD', 'Escogido00&Madrid'),
    'database': os.environ.get('MYSQLDATABASE') or os.environ.get('MYSQL_DATABASE', 'Segurcaixa'),
    'auth_plugin': 'mysql_native_password'
}

def get_db_connection():
    """Establece conexión con la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

@app.route('/')
def index():
    """Página principal del dashboard"""
    # Obtener estadísticas generales
    stats = get_statistics()
    return render_template('index.html', stats=stats)

@app.route('/leads')
def leads():
    """Lista todas las clínicas con filtros opcionales"""
    # Parámetros de filtrado
    search = request.args.get('search', '')
    estado = request.args.get('estado', '')
    con_pack = request.args.get('conPack', '')
    
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "danger")
        return render_template('leads.html', leads=[], search=search, estado=estado, con_pack=con_pack)
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Construir la consulta con filtros
        query = "SELECT * FROM leads WHERE 1=1"
        params = []
        
        if search:
            query += " AND (nombre_clinica LIKE %s OR direccion_clinica LIKE %s OR telefono LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if estado:
            query += " AND ultimo_estado = %s"
            params.append(estado)
        
        if con_pack:
            con_pack_bool = con_pack.lower() in ['true', '1', 't', 'y', 'yes']
            query += " AND conPack = %s"
            params.append(con_pack_bool)
        
        # Ordenar por nombre
        query += " ORDER BY nombre_clinica"
        
        cursor.execute(query, params)
        leads = cursor.fetchall()
        
        # Formatear fechas para visualización
        for clinica in leads:
            # Asume que hay columnas 'nombre' y 'apellidos', si no existen, usa nombre_clinica
            # No modificar los nombres de las columnas, se pasan tal cual vienen de MySQL/Excel
            # Si algún campo requiere formato especial, hazlo aquí, pero usa los nombres reales.
            pass
        
        print('DEBUG leads:', leads)
        return render_template('leads.html', leads=leads, search=search, estado=estado, con_pack=con_pack)
    
    except Error as e:
        flash(f"Error al obtener datos: {e}", "danger")
        return render_template('leads.html', leads=[], search=search, estado=estado, con_pack=con_pack)
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/clinica/<int:id>')
def ver_clinica(id):
    """Ver detalles de una clínica específica"""
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "danger")
        return redirect(url_for('leads'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM leads WHERE id = %s"
        cursor.execute(query, (id,))
        clinica = cursor.fetchone()
        
        if not clinica:
            flash("Clínica no encontrada", "warning")
            return redirect(url_for('leads'))
        
        # Formatear fecha para visualización
        if clinica.get('cita'):
            clinica['cita_formatted'] = clinica['cita'].strftime("%d/%m/%Y %H:%M")
        else:
            clinica['cita_formatted'] = "No programada"
        
        return render_template('detalle_clinica.html', clinica=clinica)
    
    except Error as e:
        flash(f"Error al obtener datos: {e}", "danger")
        return redirect(url_for('leads'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/editar_clinica/<int:id>', methods=['GET', 'POST'])
def editar_clinica(id):
    """Editar información de una clínica"""
    if request.method == 'POST':
        # Procesar el formulario de edición
        nombre = request.form.get('nombre_clinica')
        direccion = request.form.get('direccion_clinica')
        telefono = request.form.get('telefono')
        cita_str = request.form.get('cita')
        con_pack = 'conPack' in request.form
        estado = request.form.get('estado')
        
        conn = get_db_connection()
        if not conn:
            flash("Error de conexión a la base de datos", "danger")
            return redirect(url_for('leads'))
        
        try:
            cursor = conn.cursor()
            
            # Convertir fecha si se proporciona
            cita = None
            if cita_str and cita_str.strip():
                try:
                    cita = datetime.strptime(cita_str, "%Y-%m-%dT%H:%M")
                except ValueError:
                    flash("Formato de fecha incorrecto", "danger")
                    return redirect(url_for('editar_clinica', id=id))
            
            # Actualizar datos
            query = """
            UPDATE leads 
            SET nombre_clinica = %s, direccion_clinica = %s, telefono = %s, 
                cita = %s, conPack = %s, ultimo_estado = %s
            WHERE id = %s
            """
            cursor.execute(query, (nombre, direccion, telefono, cita, con_pack, estado, id))
            conn.commit()
            
            flash("Clínica actualizada correctamente", "success")
            return redirect(url_for('ver_clinica', id=id))
        
        except Error as e:
            flash(f"Error al actualizar datos: {e}", "danger")
            return redirect(url_for('editar_clinica', id=id))
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    else:
        # Mostrar formulario de edición
        conn = get_db_connection()
        if not conn:
            flash("Error de conexión a la base de datos", "danger")
            return redirect(url_for('leads'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM leads WHERE id = %s"
            cursor.execute(query, (id,))
            clinica = cursor.fetchone()
            
            if not clinica:
                flash("Clínica no encontrada", "warning")
                return redirect(url_for('leads'))
            
            # Formatear fecha para el input datetime-local
            if clinica.get('cita'):
                clinica['cita_input'] = clinica['cita'].strftime("%Y-%m-%dT%H:%M")
            else:
                clinica['cita_input'] = ""
            
            return render_template('editar_clinica.html', clinica=clinica)
        
        except Error as e:
            flash(f"Error al obtener datos: {e}", "danger")
            return redirect(url_for('leads'))
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

@app.route('/exportar_excel')
def exportar_excel():
    """Exportar datos a Excel"""
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos", "danger")
        return redirect(url_for('leads'))
    
    try:
        # Obtener datos
        df = pd.read_sql("SELECT * FROM leads", conn)
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"segurcaixa_leads_{timestamp}.xlsx"
        filepath = os.path.join("static", "exports", filename)
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Guardar Excel
        df.to_excel(filepath, index=False)
        
        # Devolver enlace de descarga
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": url_for('static', filename=f'exports/{filename}')
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
    finally:
        if conn.is_connected():
            conn.close()

def get_statistics():
    """Obtener estadísticas generales para el dashboard"""
    stats = {
        'total_leads': 0,
        'citas_programadas': 0,
        'con_pack': 0,
        'estados': {
            'no_answer': 0,
            'busy': 0,
            'completed': 0,
            'sin_estado': 0
        }
    }
    
    conn = get_db_connection()
    if not conn:
        return stats
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Total de clínicas
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        result = cursor.fetchone()
        stats['total_leads'] = result['total'] if result else 0
        
        # Citas programadas
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE cita IS NOT NULL")
        result = cursor.fetchone()
        stats['citas_programadas'] = result['total'] if result else 0
        
        # Con pack
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE conPack = TRUE")
        result = cursor.fetchone()
        stats['con_pack'] = result['total'] if result else 0
        
        # Estados
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado = 'no answer'")
        result = cursor.fetchone()
        stats['estados']['no_answer'] = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado = 'busy'")
        result = cursor.fetchone()
        stats['estados']['busy'] = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado = 'completed'")
        result = cursor.fetchone()
        stats['estados']['completed'] = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as total FROM leads WHERE ultimo_estado IS NULL")
        result = cursor.fetchone()
        stats['estados']['sin_estado'] = result['total'] if result else 0
        
        return stats
    
    except Error as e:
        print(f"Error al obtener estadísticas: {e}")
        return stats
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

import locale

# Intentar poner el locale a español para los nombres de días y meses
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        pass  # Si falla, usará inglés

def fecha_humana(fecha_str, hora_str):
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
    dia_semana = fecha.strftime("%A")  # Ej: 'martes'
    dia = fecha.day
    mes = fecha.strftime("%B")         # Ej: 'julio'
    # Capitaliza el día de la semana
    return f"{dia_semana.capitalize()} {dia} de {mes} a las {hora_str}"

@app.route('/test_citas')
def test_citas():
    return render_template('test_citas.html')

@app.route('/api/proponer_citas', methods=['POST'])
def proponer_citas():
    data = request.get_json()
    # Recoge solo pares completos
    fechas_horas_raw = []
    for i in range(1, 4):
        f = data.get(f'fecha{i}')
        h = data.get(f'hora{i}')
        if f and h:
            fechas_horas_raw.append((f, h))
    if not fechas_horas_raw:
        return jsonify({"respuesta": "Debe proporcionar al menos una fecha y hora."}), 400
    agrupadas = {}
    for fecha, hora in fechas_horas_raw:
        if fecha not in agrupadas:
            agrupadas[fecha] = []
        agrupadas[fecha].append(hora)
    partes = []
    for fecha, horas in agrupadas.items():
        fecha_fmt = fecha_humana(fecha, horas[0]).split(' a las')[0]
        if len(horas) == 1:
            partes.append(f"el {fecha_fmt} a las {horas[0]}")
        else:
            horas_txt = ' y a las '.join(horas)
            partes.append(f"el {fecha_fmt} a las {horas_txt}")
    if len(partes) == 1:
        respuesta = f"Puedo proponer {partes[0]}. ¿Le viene bien?"
    elif len(partes) == 2:
        respuesta = f"Puedo proponer {partes[0]} o {partes[1]}. ¿Cuál le viene mejor?"
    else:
        respuesta = f"Puedo proponer {', '.join(partes[:-1])} o {partes[-1]}. ¿Cuál le viene mejor?"
    return jsonify({"respuesta": respuesta})

@app.route('/test')
def test():
    return "¡Funciona en Railway!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

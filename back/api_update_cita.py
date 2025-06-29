import mysql.connector
from flask import Flask, request, jsonify
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Ajusta según tu configuración
    'database': 'tuotempo_clinicas',
    'auth_plugin': 'mysql_native_password'
}

def get_db_connection():
    """Establece conexión con la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Error al conectar a MySQL: {err}")
        return None

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint para verificar el estado de la API"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/clinica', methods=['GET'])
def get_clinica_by_telefono():
    """Obtener información de una clínica por número de teléfono"""
    telefono = request.args.get('telefono')
    
    if not telefono:
        return jsonify({"error": "Se requiere el parámetro 'telefono'"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM clinicas WHERE telefono = %s"
        cursor.execute(query, (telefono,))
        result = cursor.fetchone()
        
        if result:
            # Convertir datetime a string para JSON
            if result.get('cita'):
                result['cita'] = result['cita'].strftime("%Y-%m-%d %H:%M:%S")
            return jsonify(result)
        else:
            return jsonify({"error": "No se encontró ninguna clínica con ese número de teléfono"}), 404
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/update_cita', methods=['POST'])
def update_cita():
    """Actualizar información de cita para un número de teléfono"""
    data = request.json
    
    # Validar datos requeridos
    if not data or not data.get('telefono'):
        return jsonify({"error": "Se requiere el número de teléfono"}), 400
    
    telefono = data.get('telefono')
    cita = data.get('cita')  # Formato esperado: YYYY-MM-DD HH:MM:SS
    con_pack = data.get('conPack')  # True/False
    estado = data.get('estado')  # 'no answer', 'busy', 'completed'
    
    # Validar formato de fecha si se proporciona
    if cita:
        try:
            datetime.strptime(cita, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return jsonify({"error": "Formato de fecha incorrecto. Use YYYY-MM-DD HH:MM:SS"}), 400
    
    # Validar estado si se proporciona
    if estado and estado not in ['no answer', 'busy', 'completed']:
        return jsonify({"error": "Estado no válido. Valores permitidos: 'no answer', 'busy', 'completed'"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor()
        
        # Verificar si existe el teléfono
        check_query = "SELECT COUNT(*) FROM clinicas WHERE telefono = %s"
        cursor.execute(check_query, (telefono,))
        if cursor.fetchone()[0] == 0:
            return jsonify({"error": "No se encontró ninguna clínica con ese número de teléfono"}), 404
        
        # Construir la consulta de actualización dinámicamente
        update_parts = []
        params = []
        
        if cita is not None:
            update_parts.append("cita = %s")
            params.append(cita)
        
        if con_pack is not None:
            update_parts.append("conPack = %s")
            params.append(con_pack)
        
        if estado is not None:
            update_parts.append("ultimo_estado = %s")
            params.append(estado)
        
        if not update_parts:
            return jsonify({"message": "No se proporcionaron datos para actualizar"}), 400
        
        # Construir y ejecutar la consulta
        query = f"UPDATE clinicas SET {', '.join(update_parts)} WHERE telefono = %s"
        params.append(telefono)
        
        cursor.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({
                "success": True,
                "message": f"Información actualizada para el teléfono {telefono}",
                "rows_affected": cursor.rowcount
            })
        else:
            return jsonify({
                "success": False,
                "message": "No se actualizó ningún registro"
            }), 404
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/clinicas', methods=['GET'])
def get_all_clinicas():
    """Obtener todas las clínicas con filtros opcionales"""
    # Parámetros opcionales de filtrado
    estado = request.args.get('estado')
    con_pack = request.args.get('conPack')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM clinicas WHERE 1=1"
        params = []
        
        if estado:
            query += " AND ultimo_estado = %s"
            params.append(estado)
        
        if con_pack is not None:
            con_pack_bool = con_pack.lower() in ['true', '1', 't', 'y', 'yes']
            query += " AND conPack = %s"
            params.append(con_pack_bool)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convertir datetime a string para JSON
        for row in results:
            if row.get('cita'):
                row['cita'] = row['cita'].strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify(results)
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    logger.info("Iniciando API de actualización de citas...")
    app.run(debug=True, port=5000)

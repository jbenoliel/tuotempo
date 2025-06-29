import mysql.connector
from flask import Flask, request, jsonify
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from config import settings

# Cargar variables de entorno si existe un archivo .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_resultado_llamada.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de la base de datos usando settings
DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_DATABASE
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
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service": "API Resultado Llamada"
    })

@app.route('/api/actualizar_resultado', methods=['POST'])
def actualizar_resultado():
    """
    Actualiza el resultado de una llamada según los parámetros recibidos.
    
    Lógica:
    - Si la llamada se corta (no hay cita ni marcado como no interesado): "volver a marcar"
    - Si no toma cita (no interesado): "no interesado"
    - Si toma cita sin pack: "cita sin pack"
    - Si toma cita con pack: "cita con pack"
    """
    data = request.json
    
    # Validar datos requeridos
    if not data or not data.get('telefono'):
        return jsonify({"error": "Se requiere el número de teléfono"}), 400
    
    telefono = data.get('telefono')
    cita = data.get('cita')  # Formato esperado: YYYY-MM-DD HH:MM:SS
    con_pack = data.get('conPack', False)  # Boolean
    no_interesado = data.get('no_interesado', False)  # Boolean
    
    # Validar formato de fecha si se proporciona
    if cita:
        try:
            datetime.strptime(cita, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return jsonify({"error": "Formato de fecha incorrecto. Use YYYY-MM-DD HH:MM:SS"}), 400
    
    # Determinar el resultado de la llamada según la lógica especificada
    if cita:
        if con_pack:
            resultado = "cita con pack"
        else:
            resultado = "cita sin pack"
    elif no_interesado:
        resultado = "no interesado"
    else:
        resultado = "volver a marcar"  # Llamada cortada
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor()
        
        # Verificar si existe el teléfono
        check_query = "SELECT COUNT(*) FROM leads WHERE telefono = %s"
        cursor.execute(check_query, (telefono,))
        if cursor.fetchone()[0] == 0:
            return jsonify({"error": f"No se encontró ningún contacto con el teléfono {telefono}"}), 404
        
        # Construir la consulta de actualización
        update_query = """
        UPDATE leads 
        SET resultado_llamada = %s 
        """
        params = [resultado]
        
        # Agregar actualización de fecha de cita si se proporciona
        if cita:
            update_query += ", cita = %s, conPack = %s "
            params.append(cita)
            params.append(con_pack)
        
        # Finalizar la consulta
        update_query += "WHERE telefono = %s"
        params.append(telefono)
        
        cursor.execute(update_query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({
                "success": True,
                "message": f"Resultado de llamada actualizado para el teléfono {telefono}",
                "resultado": resultado,
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

@app.route('/api/obtener_resultados', methods=['GET'])
def obtener_resultados():
    """
    Obtener contactos filtrados por resultado de llamada
    """
    # Parámetro opcional de filtrado
    resultado = request.args.get('resultado')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, nombre, apellidos, telefono, cita, conPack, resultado_llamada FROM leads WHERE 1=1"
        params = []
        
        if resultado:
            query += " AND resultado_llamada = %s"
            params.append(resultado)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convertir datetime a string para JSON
        for row in results:
            if row.get('cita'):
                row['cita'] = row['cita'].strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "success": True,
            "count": len(results),
            "contactos": results
        })
    
    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos: {err}")
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    logger.info("Iniciando API de Resultado de Llamada...")
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)

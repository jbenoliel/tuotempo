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
    Actualiza el resultado y los datos de una llamada para un lead específico.
    Este endpoint recibe datos de la llamada desde un sistema externo (como NLPearl) y los guarda en la BD.
    """
    data = request.json
    logger.info(f"Recibida petición para actualizar resultado: {data}")

    # Validar datos requeridos
    if not data or not data.get('telefono'):
        logger.error("Petición rechazada: No se proporcionó número de teléfono.")
        return jsonify({"error": "Se requiere el número de teléfono"}), 400

    telefono = data.get('telefono')

    # Recoger todos los campos posibles de la petición
    update_fields = {

        'status_level_1': data.get('status_level_1'),
        'status_level_2': data.get('status_level_2'),
        

        # Nuevos campos detallados
        'conPack': data.get('conPack'),
        'hora_rellamada': data.get('horaRellamada'),
        'error_tecnico': data.get('errorTecnico'),
        'razon_vuelta_a_llamar': data.get('razonvueltaallamar'),
        'razon_no_interes': data.get('razonNoInteres')
    }

    # --- Mapeos de códigos compactos a descripciones ---
    # 1) Razones de "No Interesado"
    codigo_no_interes = data.get('codigoNoInteres')
    mapa_no_interes = {
        'no disponibilidad': 'no disponibilidad cliente',
        'descontento': 'Descontento con Adeslas',
        'bajaProxima': 'Próxima baja',
        'otros': 'No da motivos'
    }
    if codigo_no_interes in mapa_no_interes:
        update_fields['status_level_1'] = 'No Interesado'
        update_fields['status_level_2'] = mapa_no_interes[codigo_no_interes]

    # 2) Razones de "Volver a llamar"
    codigo_volver_llamar = data.get('codigoVolverLlamar')
    mapa_volver_llamar = {
        'buzon': 'buzón',
        'interrupcion': 'no disponible cliente',
        'proble tecnico': 'Interesado. Problema técnico',
        'proble_tecnico': 'Interesado. Problema técnico'
    }
    if codigo_volver_llamar in mapa_volver_llamar:
        update_fields['status_level_1'] = 'Volver a llamar'
        update_fields['status_level_2'] = mapa_volver_llamar[codigo_volver_llamar]

    # Lógica de negocio para campos especiales
    if data.get('noInteresado'):
        update_fields['status_level_1'] = 'No Interesado'

    # Si llega una nueva cita, actualizamos el campo 'fecha_cita'
    if data.get('nuevaCita'):
        update_fields['fecha_cita'] = data.get('nuevaCita') # Guardamos la fecha/hora de la cita

    # Para mantener la compatibilidad, si llega status_level_2, lo usamos también para el campo antiguo 'resultado_ultima_gestion'

    # Filtrar campos que son None para no sobreescribir datos existentes con nulos en la BD
    update_data = {k: v for k, v in update_fields.items() if v is not None}

    if not update_data:
        return jsonify({"error": "No se proporcionaron datos para actualizar"}), 400

    # Construir la consulta SQL dinámicamente
    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    sql_query = f"UPDATE leads SET {set_clause} WHERE telefono = %s"
    
    values = list(update_data.values())
    values.append(telefono)

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(sql_query, tuple(values))

        if cursor.rowcount == 0:
            logger.warning(f"No se encontró ningún lead con el teléfono: {telefono}")
            return jsonify({"error": f"No se encontró ningún lead con el teléfono {telefono}"}), 404

        conn.commit()
        logger.info(f"Lead con teléfono {telefono} actualizado correctamente. {cursor.rowcount} fila(s) afectada(s).")

        return jsonify({
            "success": True,
            "message": f"Lead {telefono} actualizado correctamente."
        })

    except mysql.connector.Error as err:
        logger.error(f"Error de base de datos al actualizar el lead {telefono}: {err}")
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error de base de datos: {str(err)}"}), 500
    finally:
        if conn and conn.is_connected():
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

from flask import Flask, request, jsonify
from tuotempo_api import TuoTempoAPI
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/centers', methods=['GET'])
def get_centers():
    province = request.args.get('province')
    
    api = TuoTempoAPI(
        lang=request.args.get('lang', 'es'),
        environment=request.args.get('environment', 'PRE')
    )
    
    centers_response = api.get_centers(province=province)
    return jsonify(centers_response)

@app.route('/slots', methods=['GET'])
def get_slots():
    api = TuoTempoAPI(
        lang=request.args.get('lang', 'es'),
        environment=request.args.get('environment', 'PRE')
    )
    
    activity_id = request.args.get('activity_id', 'sc159232371eb9c1')  # Default: primera visita
    area_id = request.args.get('area_id')
    
    if not area_id:
        return jsonify({"error": "area_id is required"}), 400
    
    start_date = request.args.get('start_date')
    if not start_date:
        start_date = datetime.now().strftime("%d/%m/%Y")
    
    resource_id = request.args.get('resource_id')
    min_time = request.args.get('min_time')
    max_time = request.args.get('max_time')
    
    slots_response = api.get_available_slots(
        activity_id=activity_id,
        area_id=area_id,
        start_date=start_date,
        resource_id=resource_id,
        min_time=min_time,
        max_time=max_time
    )
    
    return jsonify(slots_response)

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    
    if not all(k in data for k in ['fname', 'lname', 'birthday', 'phone']):
        return jsonify({"error": "Missing required fields"}), 400
    
    api = TuoTempoAPI(
        lang=request.args.get('lang', 'es'),
        environment=request.args.get('environment', 'PRE')
    )
    
    user_response = api.register_non_insured_user(
        fname=data['fname'],
        lname=data['lname'],
        birthday=data['birthday'],
        phone=data['phone']
    )
    
    return jsonify(user_response)

@app.route('/confirm', methods=['POST'])
def confirm_appointment():
    data = request.json
    
    if not all(k in data for k in ['availability', 'communication_phone']):
        return jsonify({"error": "Missing required fields"}), 400
    
    api = TuoTempoAPI(
        lang=request.args.get('lang', 'es'),
        environment=request.args.get('environment', 'PRE')
    )
    
    # Registrar usuario primero si se proporcionan datos
    if all(k in data for k in ['fname', 'lname', 'birthday', 'phone']):
        user_response = api.register_non_insured_user(
            fname=data['fname'],
            lname=data['lname'],
            birthday=data['birthday'],
            phone=data['phone']
        )
        
        if user_response.get("result") != "OK":
            return jsonify({"error": "Failed to register user", "details": user_response}), 400
    
    # Confirmar cita
    appointment_response = api.confirm_appointment(
        availability=data['availability'],
        communication_phone=data['communication_phone']
    )
    
    return jsonify(appointment_response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

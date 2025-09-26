"""
Endpoint simplificado para debugging de leads
"""

from flask import Flask, request, jsonify
from db import get_connection
from datetime import datetime

def create_simple_leads_endpoint():
    """Crea un endpoint simple para debuggear leads"""
    
    app = Flask(__name__)
    
    @app.route('/debug/leads', methods=['GET'])
    def debug_leads():
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Query muy simple sin filtros complicados
            cursor.execute("""
                SELECT 
                    id, nombre, apellidos, telefono, telefono2, ciudad, nombre_clinica,
                    call_status, selected_for_calling, call_priority, call_attempts_count
                FROM leads 
                ORDER BY id DESC
                LIMIT 20
            """)
            leads = cursor.fetchall()
            
            # Contar total
            cursor.execute("SELECT COUNT(*) as total FROM leads")
            total = cursor.fetchone()['total']
            
            # Formatear respuesta
            for lead in leads:
                # call_status puede ser NULL (sin llamadas previas)
                # NULL es un valor válido, no necesita conversión
                if lead['selected_for_calling'] is None:
                    lead['selected_for_calling'] = False
                if lead['call_priority'] is None:
                    lead['call_priority'] = 3
            
            return jsonify({
                "success": True,
                "leads": leads,
                "total": total,
                "message": f"Devolviendo {len(leads)} de {total} leads total",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        finally:
            if 'conn' in locals():
                conn.close()
    
    return app

if __name__ == "__main__":
    app = create_simple_leads_endpoint()
    print("🧪 Servidor de debugging iniciado en http://localhost:5001")
    print("Prueba: http://localhost:5001/debug/leads")
    app.run(debug=True, port=5001)

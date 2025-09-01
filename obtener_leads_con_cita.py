import sys
from db import get_connection

def obtener_leads_con_cita():
    """Obtiene y muestra los leads que tienen una cita programada."""
    connection = None
    try:
        connection = get_connection()
        if not connection:
            print("Error: No se pudo obtener la conexión desde db.py", file=sys.stderr)
            return

        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT nombre, apellidos, telefono
        FROM leads
        WHERE status_level_1 = 'Cita Agendada'
        ORDER BY nombre, apellidos;
        """
        
        cursor.execute(query)
        leads = cursor.fetchall()
        
        if not leads:
            print("No se encontraron leads con citas programadas.")
            return

        print("--- Leads con Cita Programada ---")
        for lead in leads:
            nombre_completo = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}".strip()
            telefono = lead.get('telefono', 'N/A')
            print(f"- Nombre: {nombre_completo}, Teléfono: {telefono}")
        print("---------------------------------")

    except Exception as e:
        print(f"Ocurrió un error: {e}", file=sys.stderr)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    obtener_leads_con_cita()

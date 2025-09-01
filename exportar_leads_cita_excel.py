import sys
import pandas as pd
from db import get_connection
from datetime import datetime

def exportar_leads_con_cita_a_excel():
    """Obtiene los leads con cita y los exporta a un archivo Excel."""
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
        
        print("Ejecutando consulta para obtener leads con cita...")
        cursor.execute(query)
        leads = cursor.fetchall()
        
        if not leads:
            print("No se encontraron leads con citas programadas para exportar.")
            return

        print(f"Se encontraron {len(leads)} leads. Creando archivo Excel...")

        # Convertir a DataFrame de pandas
        df = pd.DataFrame(leads)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_con_cita_{timestamp}.xlsx"
        
        # Exportar a Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"¡Éxito! Se ha generado el archivo Excel: {filename}")

    except ImportError:
        print("Error: Las librerías 'pandas' y 'openpyxl' son necesarias.", file=sys.stderr)
        print("Por favor, instálalas ejecutando: pip install pandas openpyxl", file=sys.stderr)
    except Exception as e:
        print(f"Ocurrió un error: {e}", file=sys.stderr)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    exportar_leads_con_cita_a_excel()

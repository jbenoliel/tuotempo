import sys
from db import get_connection

def add_index_to_status_level_1():
    """Añade un índice a la columna status_level_1 de la tabla leads."""
    connection = None
    try:
        connection = get_connection()
        if not connection:
            print("Error: No se pudo obtener la conexión desde db.py", file=sys.stderr)
            return

        cursor = connection.cursor()
        
        # Comprobar si el índice ya existe
        cursor.execute("SHOW INDEX FROM leads WHERE Key_name = 'idx_status_level_1'")
        if cursor.fetchone():
            print("El índice 'idx_status_level_1' ya existe en la tabla 'leads'. No se requiere ninguna acción.")
            return

        print("Añadiendo índice 'idx_status_level_1' a la tabla 'leads'. Esto puede tardar unos minutos...")
        # Añadir el índice
        cursor.execute("CREATE INDEX idx_status_level_1 ON leads(status_level_1)")
        connection.commit()
        print("¡Éxito! El índice 'idx_status_level_1' ha sido añadido correctamente.")

    except Exception as e:
        print(f"Ocurrió un error al añadir el índice: {e}", file=sys.stderr)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    add_index_to_status_level_1()

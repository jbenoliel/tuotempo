import sys
from db import get_connection

def describe_table(table_name='leads'):
    """Se conecta a la BD y ejecuta DESCRIBE en la tabla especificada."""
    connection = None
    try:
        print(f"Intentando conectar a la base de datos para describir la tabla '{table_name}'...")
        connection = get_connection()
        if not connection:
            print("Error: No se pudo obtener la conexión desde db.py")
            return

        cursor = connection.cursor()
        print(f"Ejecutando: DESCRIBE {table_name}")
        cursor.execute(f"DESCRIBE {table_name}")
        
        print("\n--- ESTRUCTURA DE LA TABLA 'leads' ---")
        print(f"{'Campo':<30} | {'Tipo':<20} | {'Nulo':<5} | {'Clave':<5} | {'Default':<15}")
        print('-'*90)
        
        for row in cursor.fetchall():
            field, type, null, key, default = row[:5]
            print(f"{field:<30} | {type:<20} | {null:<5} | {key:<5} | {str(default):<15}")
            
        print("-------------------------------------\n")

    except Exception as e:
        print(f"\nOcurrió un error al describir la tabla: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    describe_table()

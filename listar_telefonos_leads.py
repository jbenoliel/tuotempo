import mysql.connector
from config import settings

DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'database': settings.DB_DATABASE
}

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellidos, telefono, telefono2 FROM leads LIMIT 20")
    print("Primeros 20 registros en leads (puede haber teléfonos vacíos):")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Nombre: {row[1]} {row[2]}, Teléfono1: '{row[3]}', Teléfono2: '{row[4]}'")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

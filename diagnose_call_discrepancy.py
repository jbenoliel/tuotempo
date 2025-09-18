import os
import mysql.connector
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Establece una conexión con la base de datos de Railway."""
    try:
        # Usar la misma configuración que otras partes de la aplicación
        DB_CONFIG = {
            'host': os.getenv('MYSQLHOST'),
            'port': int(os.getenv('MYSQLPORT', 3306)),
            'user': os.getenv('MYSQLUSER'),
            'password': os.getenv('MYSQLPASSWORD'),
            'database': os.getenv('MYSQLDATABASE'),
            'ssl_disabled': os.getenv('MYSQL_SSL_DISABLED', 'true').lower() == 'true'
        }
        
        # Filtrar claves None para evitar errores en connect
        DB_CONFIG = {k: v for k, v in DB_CONFIG.items() if v is not None}

        if not all([DB_CONFIG.get('host'), DB_CONFIG.get('user'), DB_CONFIG.get('password'), DB_CONFIG.get('database')]):
            print("\033[91mError: Faltan variables de entorno para la base de datos (MYSQLHOST, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE).\033[0m")
            return None

        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"\033[91mError al conectar a MySQL: {e}\033[0m")
        # Intentar un fallback común para Railway si falla la conexión SSL
        if 'ssl' in str(e).lower():
            print("Intentando fallback sin SSL...")
            try:
                DB_CONFIG['ssl_disabled'] = True
                connection = mysql.connector.connect(**DB_CONFIG)
                return connection
            except mysql.connector.Error as e2:
                print(f"\033[91mEl fallback también falló: {e2}\033[0m")
        return None

def run_diagnostics():
    """Ejecuta una serie de consultas para diagnosticar la discrepancia de llamadas."""
    conn = get_db_connection()
    if not conn:
        return

    print("\033[1m\n--- DIAGNÓSTICO DE DISCREPANCIA DE LLAMADAS ---\033[0m")

    try:
        cursor = conn.cursor()

        queries = {
            "Total de llamadas programadas (call_schedule)": "SELECT COUNT(*) FROM call_schedule;",
            "Llamadas programadas con 'last_outcome' no nulo": "SELECT COUNT(*) FROM call_schedule WHERE last_outcome IS NOT NULL;",
            "Total de llamadas reales (pearl_calls)": "SELECT COUNT(*) FROM pearl_calls;",
            "Distribución de estados en 'call_schedule'": "SELECT status, COUNT(*) FROM call_schedule GROUP BY status;",
            "Llamadas programadas pendientes (status='pending')": "SELECT COUNT(*) FROM call_schedule WHERE status = 'pending';",
            "Llamadas programadas para el futuro (scheduled_at > NOW())": "SELECT COUNT(*) FROM call_schedule WHERE scheduled_at > NOW();",
            "Llamadas programadas 'pending' en el pasado": "SELECT COUNT(*) FROM call_schedule WHERE status = 'pending' AND scheduled_at < NOW();"
        }

        for description, query in queries.items():
            print(f"\n\033[94m-> {description}:\033[0m")
            cursor.execute(query)
            results = cursor.fetchall()
            
            print("-" * 40)
            if 'GROUP BY' in query.upper():
                if not results:
                    print("  No results found.")
                for row in results:
                    status_name = row[0] if row[0] is not None else "NULL"
                    count = row[1]
                    print(f"  - Status '{status_name}': {count:,}")
            else:
                count = results[0][0] if results else 0
                print(f"  Total: {count:,}")
            print("-" * 40)

    except mysql.connector.Error as e:
        print(f"\033[91mError durante la ejecución de la consulta: {e}\033[0m")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("\n\033[1m--- Diagnóstico finalizado ---\033[0m")

if __name__ == "__main__":
    run_diagnostics()

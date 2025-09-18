import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        DB_CONFIG = {
            'host': os.getenv('MYSQLHOST'),
            'port': int(os.getenv('MYSQLPORT', 3306)),
            'user': os.getenv('MYSQLUSER'),
            'password': os.getenv('MYSQLPASSWORD'),
            'database': os.getenv('MYSQLDATABASE'),
            'ssl_disabled': os.getenv('MYSQL_SSL_DISABLED', 'true').lower() == 'true'
        }
        DB_CONFIG = {k: v for k, v in DB_CONFIG.items() if v is not None}
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def run_query():
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        query = "SELECT status, COUNT(*) FROM call_schedule GROUP BY status;"
        print(f"Executing Query: {query}")
        cursor.execute(query)
        results = cursor.fetchall()
        print("--- Results ---")
        if not results:
            print("No results found.")
        for row in results:
            status_name = row[0] if row[0] is not None else "NULL"
            count = row[1]
            print(f"Status: {status_name}, Count: {count}")
        print("--- End ---")

    except Exception as e:
        print(f"Query Error: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    run_query()

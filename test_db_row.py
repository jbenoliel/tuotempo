import mysql.connector
import json

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Escogido00&Madrid',
    'database': 'Segurcaixa',
    'auth_plugin': 'mysql_native_password'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clinicas LIMIT 1;")
    row = cursor.fetchone()
    print(json.dumps(row, indent=4, ensure_ascii=False))
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

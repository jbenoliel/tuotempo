import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Escogido00&Madrid',
    'database': 'Segurcaixa',
    'auth_plugin': 'mysql_native_password'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clinicas;")
    count = cursor.fetchone()[0]
    print(f"Total registros en clinicas: {count}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
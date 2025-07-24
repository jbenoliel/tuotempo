import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

print("Testing MySQL connection...")
print(f"Host: {os.getenv('MYSQLHOST')}")
print(f"User: {os.getenv('MYSQLUSER')}")
print(f"Database: {os.getenv('MYSQLDATABASE')}")
print(f"Port: {os.getenv('MYSQLPORT')}")

try:
    conn = mysql.connector.connect(
        host=os.getenv('MYSQLHOST'),
        user=os.getenv('MYSQLUSER'),
        password=os.getenv('MYSQLPASSWORD'),
        database=os.getenv('MYSQLDATABASE'),
        port=int(os.getenv('MYSQLPORT', 3306))
    )
    print("SUCCESS: Connected to MySQL!")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")

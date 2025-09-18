import os
import pymysql
from dotenv import load_dotenv
import argparse

load_dotenv()

def get_db_connection():
    try:
        return pymysql.connect(
            host=os.getenv('MYSQLHOST'),
            port=int(os.getenv('MYSQLPORT', 3306)),
            user=os.getenv('MYSQLUSER'),
            password=os.getenv('MYSQLPASSWORD'),
            database=os.getenv('MYSQLDATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def cleanup_schedules(dry_run=True):
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Count records to be deleted
            cursor.execute("SELECT COUNT(*) as total FROM call_schedule WHERE status = 'cancelled'")
            count_to_delete = cursor.fetchone()['total']
            
            print(f"Found {count_to_delete:,} records with status 'cancelled' to delete.")

            if count_to_delete == 0:
                print("No records to delete. The table is clean.")
                return

            if dry_run:
                print("\nDRY RUN MODE: No records will be deleted.")
                print("To execute the deletion, run the script with the --execute flag.")
            else:
                print("\nEXECUTING DELETION...")
                deleted_count = cursor.execute("DELETE FROM call_schedule WHERE status = 'cancelled'")
                conn.commit()
                print(f"Successfully deleted {deleted_count:,} records.")

    except Exception as e:
        print(f"An error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup cancelled records from call_schedule table.")
    parser.add_argument('--execute', action='store_true', help='Actually execute the deletion. Otherwise, runs in dry-run mode.')
    args = parser.parse_args()

    cleanup_schedules(dry_run=not args.execute)

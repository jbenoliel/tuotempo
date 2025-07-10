"""Quick diagnostic script to inspect the `leads` table.

Run with: `python check_leads.py`
It prints total number of leads and the first 15 rows with key columns so we can
verify that the ETL/import has worked correctly.
"""
from pprint import pprint

from api_pearl_calls import get_connection


def main():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM leads")
    total = cursor.fetchone()["total"]
    print(f"Total leads in DB: {total}\n")

    cursor.execute(
        """
        SELECT id, nombre, telefono, telefono2, ciudad, nombre_clinica AS clinica,
               call_status AS status, call_priority AS priority,
               selected_for_calling AS selected, updated_at
        FROM leads
        ORDER BY updated_at DESC
        LIMIT 15
        """
    )
    rows = cursor.fetchall()
    pprint(rows)


if __name__ == "__main__":
    main()

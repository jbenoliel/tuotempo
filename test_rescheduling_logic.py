import pymysql
from dotenv import load_dotenv
import os
from reprogramar_llamadas_simple import simple_reschedule_failed_call, get_pymysql_connection

load_dotenv()

TEST_LEAD_ID = None

def setup_test_lead():
    """Crea un lead de prueba en la base de datos y devuelve su ID."""
    global TEST_LEAD_ID
    conn = get_pymysql_connection()
    if not conn:
        raise Exception("No se pudo conectar a la base de datos para la configuración.")
    
    try:
        with conn.cursor() as cursor:
            # Limpiar cualquier lead de prueba anterior
            cursor.execute("DELETE FROM leads WHERE nombre = 'TEST_LEAD_SCHEDULER'")
            
            # Crear un nuevo lead de prueba
            sql = """
                INSERT INTO leads (nombre, apellidos, telefono, lead_status, call_attempts_count)
                VALUES ('TEST_LEAD_SCHEDULER', 'Test', '999999999', 'open', 0)
            """
            cursor.execute(sql)
            TEST_LEAD_ID = cursor.lastrowid
            conn.commit()
            print(f"Lead de prueba creado con ID: {TEST_LEAD_ID}")
            return TEST_LEAD_ID
    finally:
        if conn:
            conn.close()

def cleanup():
    """Limpia los datos de prueba (lead y schedule)."""
    if not TEST_LEAD_ID:
        return
    
    conn = get_pymysql_connection()
    if not conn:
        print("No se pudo conectar a la base de datos para la limpieza.")
        return

    try:
        with conn.cursor() as cursor:
            print(f"Limpiando datos para lead_id: {TEST_LEAD_ID}...")
            cursor.execute("DELETE FROM call_schedule WHERE lead_id = %s", (TEST_LEAD_ID,))
            print(f"- {cursor.rowcount} registros eliminados de call_schedule.")
            cursor.execute("DELETE FROM leads WHERE id = %s", (TEST_LEAD_ID,))
            print(f"- {cursor.rowcount} registros eliminados de leads.")
            conn.commit()
            print("Limpieza completada.")
    finally:
        if conn:
            conn.close()

def run_test():
    """Ejecuta la prueba de reprogramación."""
    lead_id = None
    try:
        lead_id = setup_test_lead()
        if not lead_id:
            raise Exception("No se pudo crear el lead de prueba.")

        print("\n--- PASO 1: Simular llamada fallida y solicitar reprogramación ---")
        # Simulamos una llamada con resultado 'no_answer'
        rescheduled = simple_reschedule_failed_call(lead_id, 'no_answer')
        
        if rescheduled:
            print("\033[92mÉXITO: La función simple_reschedule_failed_call devolvió True.\033[0m")
        else:
            print("\033[91mFALLO: La función simple_reschedule_failed_call devolvió False.\033[0m")
            return

        print("\n--- PASO 2: Verificar que se creó la entrada en call_schedule ---")
        conn = get_pymysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM call_schedule WHERE lead_id = %s AND status = 'pending'", (lead_id,))
            new_schedule = cursor.fetchone()
        
        if new_schedule:
            print("\033[92mVERIFICACIÓN CORRECTA: Se encontró una nueva llamada programada 'pending'.\033[0m")
            print(f"  - Datos: {new_schedule}")
        else:
            print("\033[91mVERIFICACIÓN FALLIDA: No se encontró una nueva llamada programada.\033[0m")

    except Exception as e:
        print(f"Ocurrió un error durante la prueba: {e}")
    finally:
        print("\n--- PASO 3: Limpieza de datos de prueba ---")
        cleanup()

if __name__ == "__main__":
    run_test()

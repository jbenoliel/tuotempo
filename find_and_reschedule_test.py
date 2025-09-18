import pymysql
from dotenv import load_dotenv
import os
from reprogramar_llamadas_simple import simple_reschedule_failed_call, get_pymysql_connection

load_dotenv()

def find_safe_lead():
    """Encuentra un lead seguro para usar en la prueba."""
    conn = get_pymysql_connection()
    if not conn:
        raise Exception("No se pudo conectar a la base de datos.")
    
    try:
        with conn.cursor() as cursor:
            # Buscar un lead abierto, no en reserva automática, y con pocos intentos
            query = """
                SELECT id, nombre, apellidos, lead_status, call_attempts_count
                FROM leads
                WHERE
                    (lead_status = 'open' OR lead_status IS NULL)
                    AND reserva_automatica = FALSE
                    AND call_attempts_count < 3
                ORDER BY
                    updated_at ASC
                LIMIT 1;
            """
            cursor.execute(query)
            lead = cursor.fetchone()
            return lead
    finally:
        if conn:
            conn.close()

def verify_schedule(lead_id):
    """Verifica si se creó una nueva entrada en call_schedule."""
    conn = get_pymysql_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM call_schedule WHERE lead_id = %s AND status = 'pending' ORDER BY created_at DESC LIMIT 1", (lead_id,))
            return cursor.fetchone()
    finally:
        if conn:
            conn.close()

def run_safe_test():
    """Ejecuta la prueba de reprogramación de forma segura en un lead existente."""
    print("--- PASO 1: Buscando un lead seguro para la prueba ---")
    safe_lead = find_safe_lead()

    if not safe_lead:
        print("\033[91mNo se encontró ningún lead seguro para realizar la prueba. Abortando.\033[0m")
        return

    lead_id = safe_lead['id']
    print(f"Lead encontrado: ID={lead_id}, Nombre='{safe_lead['nombre']}', Intentos={safe_lead['call_attempts_count']}")

    print("\n--- PASO 2: Simular llamada fallida y solicitar reprogramación ---")
    # Simulamos una llamada con resultado 'no_answer'
    rescheduled = simple_reschedule_failed_call(lead_id, 'no_answer')

    if rescheduled:
        print("\033[92mÉXITO: La función simple_reschedule_failed_call devolvió True.\033[0m")
    else:
        print("\033[91mFALLO: La función simple_reschedule_failed_call devolvió False.\033[0m")
        print("Esto puede ser normal si el lead alcanzó el máximo de intentos.")
        return

    print("\n--- PASO 3: Verificar que se creó la entrada en call_schedule ---")
    new_schedule = verify_schedule(lead_id)

    if new_schedule:
        print("\033[92mVERIFICACIÓN CORRECTA: Se encontró una nueva llamada programada 'pending'.\033[0m")
        print(f"  - Datos de la nueva programación: {new_schedule}")
    else:
        print("\033[91mVERIFICACIÓN FALLIDA: No se encontró una nueva llamada programada.\033[0m")

if __name__ == "__main__":
    run_safe_test()

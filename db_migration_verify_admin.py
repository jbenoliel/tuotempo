import logging
from db import get_connection

def run_migration():
    """Asegura que el usuario 'admin' exista, sea administrador y esté verificado."""
    logging.info("--- Ejecutando migración de datos: Verificar usuario admin ---")
    db_conn = None
    try:
        db_conn = get_connection()
        if not db_conn:
            logging.error("[MIGRATION-VERIFY-ADMIN] No se pudo obtener conexión a la base de datos.")
            return False

        cursor = db_conn.cursor()

        # Esta consulta actualiza al usuario 'admin' para asegurar que es admin y está verificado.
        # Es segura de ejecutar múltiples veces.
        update_query = """
        UPDATE usuarios 
        SET is_admin = 1, email_verified = 1 
        WHERE username = 'admin';
        """

        cursor.execute(update_query)
        
        if cursor.rowcount > 0:
            logging.info(f"✅ Usuario 'admin' actualizado exitosamente ({cursor.rowcount} fila afectada).")
        else:
            logging.info("Usuario 'admin' ya estaba configurado correctamente o no fue encontrado. No se realizaron cambios.")

        db_conn.commit()
        cursor.close()
        logging.info("--- Migración 'Verificar usuario admin' completada ---")
        return True

    except Exception as e:
        logging.error(f"❌ Error durante la migración 'Verificar usuario admin': {e}", exc_info=True)
        if db_conn:
            db_conn.rollback()
        return False
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_migration()

import time
import traceback
from create_mysql_database import main as update_database

if __name__ == "__main__":
    print("Inicio de actualización automática de la base de datos cada minuto.")
    while True:
        print("\n[INFO] Ejecutando actualización de datos...")
        try:
            update_database()
            print("[OK] Actualización completada.")
        except Exception as e:
            print("[ERROR] Fallo en la actualización:", e)
            traceback.print_exc()
        print("[INFO] Esperando 60 segundos para la próxima actualización...")
        time.sleep(60)

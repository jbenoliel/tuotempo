"""Prueba end-to-end de reserva en la API de Tuotempo

1. Obtiene un slot disponible (disponibilidades)
2. Registra un usuario no asegurado
3. Confirma la cita

Uso:
    python test_reserva_e2e.py --activity ACTIVITY_ID --area AREA_ID [--date DD/MM/YYYY] [--env PRE|PRO]

Si no se especifica fecha, usa la fecha de hoy.
El script imprime los pasos y la respuesta final.
"""
import argparse
import logging
import random
import string
from datetime import datetime

from tuotempo_api import TuoTempoAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def random_string(n=6):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def random_phone():
    # Genera un número español ficticio pero válido (empieza por 6 o 7 y 9 dígitos)
    prefix = random.choice(['6', '7'])
    return prefix + ''.join(random.choices(string.digits, k=8))

def main():
    parser = argparse.ArgumentParser(description="Prueba end-to-end de reserva Tuotempo")
    parser.add_argument('--activity', required=True, help='ID de la actividad (activityid)')
    parser.add_argument('--area', required=True, help='ID de la clínica/área (areaId)')
    parser.add_argument('--date', help='Fecha inicio búsqueda (DD/MM/YYYY). Por defecto: hoy')
    parser.add_argument('--env', default='PRE', choices=['PRE', 'PRO'], help='Entorno PRE o PRO (default PRE)')
    parser.add_argument('--cancel', action='store_true', help='Cancelar la cita creada')
    args = parser.parse_args()

    start_date = args.date or datetime.now().strftime('%d/%m/%Y')
    logging.info(f"Buscando slots para fecha {start_date} ...")

    api = TuoTempoAPI(environment=args.env)

    slots_resp = api.get_available_slots(activity_id=args.activity, area_id=args.area, start_date=start_date)
    if slots_resp.get('result') != 'OK':
        logging.error(f"Error al obtener slots: {slots_resp}")
        return

    availabilities = slots_resp.get('return', {}).get('results', {}).get('availabilities', [])
    if not availabilities:
        logging.warning("No hay slots disponibles para la fecha indicada")
        return

    slot = availabilities[0]
    logging.info(f"Usando slot: {slot}")

    # Datos de usuario aleatorios
    fname = 'Test' + random_string()
    lname = 'User' + random_string()
    birthday = '01/01/1990'
    phone = random_phone()

    logging.info(f"Registrando usuario {fname} {lname} ({phone}) ...")
    reg_resp = api.register_non_insured_user(fname=fname, lname=lname, birthday=birthday, phone=phone)
    if not api.session_id:
        logging.error(f"Fallo al registrar usuario: {reg_resp}")
        return

    logging.info("Confirmando cita ...")
    confirm_resp = api.confirm_appointment(availability=slot, communication_phone=phone)

    print("\n======= RESPUESTA FINAL ===========")
    print(confirm_resp)

    if args.cancel and confirm_resp.get('result') == 'OK':
        resid = confirm_resp.get('return') or confirm_resp.get('resid')
        if resid:
            logging.info(f"Cancelando cita {resid} ...")
            cancel_resp = api.cancel_appointment(resid=resid, reason="Prueba automatizada")
            print("\n======= CANCELACIÓN ===========")
            print(cancel_resp)

if __name__ == '__main__':
    main()

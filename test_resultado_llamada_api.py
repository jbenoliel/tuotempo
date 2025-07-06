# -*- coding: utf-8 -*-
"""Conjunto de pruebas para la API /api/actualizar_resultado

Ejecuta llamadas HTTP contra la API de Resultado de Llamada que corre (por
omisión) en http://127.0.0.1:5001.

Cada prueba muestra:
• El nombre del escenario.
• El JSON que se envía.
• Código de estado HTTP.
• Respuesta JSON formateada.

Antes de ejecutar:
1. Asegúrate de que la API esté ejecutándose:  `python api_resultado_llamada.py`.
2. Verifica que existan en la tabla `leads` los teléfonos usados en los tests
   (se crean de ejemplo).  Si no existen, ajusta los números o crea un lead
   manualmente.
3. Instala dependencias de test: `pip install requests` (ya incluida en la venv
   por defecto).
"""

import json
import time
from datetime import datetime, timedelta

import mysql.connector
import requests

from config import settings

API_BASE = "http://127.0.0.1:5001/api"

# ---- Utilidades teléfonos de prueba ----
TEST_PHONE_COUNT = 4  # cuántos teléfonos distintos usaremos en las pruebas


def get_test_phones(n: int):
    """Genera n teléfonos secuenciales 700000000, 700000001… y se asegura de que existan en la tabla leads."""
    conn = mysql.connector.connect(**DB_CFG)
    phones = []
    next_num = 700000000
    try:
        with conn.cursor() as cur:
            while len(phones) < n:
                candidate = str(next_num)
                # Insertar si no existe
                cur.execute("SELECT 1 FROM leads WHERE telefono=%s", (candidate,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO leads (nombre, telefono) VALUES (%s, %s)", ("Test", candidate))
                    conn.commit()
                phones.append(candidate)
                next_num += 1
    finally:
        conn.close()
    return phones

DB_CFG = {
    "host": settings.DB_HOST,
    "port": settings.DB_PORT,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD,
    "database": settings.DB_DATABASE,
}

def ensure_phone_exists(phone: str):
    """Crea un lead mínimo si no existe (para pruebas exitosas)."""
    conn = mysql.connector.connect(**DB_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM leads WHERE telefono=%s", (phone,))
            if cur.fetchone():
                return
            cur.execute(
                "INSERT INTO leads (nombre, telefono) VALUES (%s, %s)",
                ("Test", phone),
            )
            conn.commit()
    finally:
        conn.close()


def run_test(name: str, payload: dict, expected_status: int):
    print("\n" + "=" * 60)
    print(f"TEST: {name}")
    print("=" * 60)
    print("Payload enviado:\n" + json.dumps(payload, indent=2, default=str))

    resp = requests.post(f"{API_BASE}/actualizar_resultado", json=payload)

    print(f"\nHTTP {resp.status_code} (esperado {expected_status})")
    try:
        print("Respuesta JSON:\n" + json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print("Respuesta no es JSON:\n" + resp.text)


def main():
    phones = get_test_phones(TEST_PHONE_COUNT)


    # 4. Éxito mínimo – actualiza call_id
    run_test(
        "Actualización mínima (200)",
        payload={"telefono": phones[0], "status_level_1": "Volver a llamar", "status_level_2": "buzón"},
        expected_status=200,
    )

    # 5. Éxito volver a llamar con código mapeado
    run_test(
        "Volver a llamar (200)",
        payload={
            "telefono": phones[1],
            "codigoVolverLlamar": "buzon",
            "horaRellamada": (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        },
        expected_status=200,
    )

    # 6. Éxito con noInteresado -> status_level_1="No Interesado"
    run_test(
        "No interesado (200)",
        payload={
            "telefono": phones[2],
            "noInteresado": True,
            "status_level_2": "Descontento Adeslas",
        },
        expected_status=200,
    )

    # 7. Éxito con nueva cita y datos completos
    run_test(
        "Nueva cita con pack (200)",
        payload={
            "telefono":     phones[3],
            "nuevaCita": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            "conPack": True,
            "status_level_1": "Cita Agendada",
            "status_level_2": "con pack",
            "call_duration": 120,
        },
        expected_status=200,
    )


if __name__ == "__main__":
    main()

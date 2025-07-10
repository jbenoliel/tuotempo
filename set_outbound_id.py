"""Utility script to automatically fetch the outbound campaign ID from Pearl AI
and store it in a local .env file so the application can use it as the default
campaign when making calls.

Usage (from project root virtual-env):
    python set_outbound_id.py "Segurcaixa III- POC Tuotempo"
If no name is provided, it lists campaigns and asks interactively.
"""
from pathlib import Path
import sys
import json
import logging
from typing import Optional

from pearl_caller import PearlCaller, PearlAPIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


ENV_FILE = Path(__file__).parent / ".env"


def update_env(outbound_id: str):
    """Add or update PEARL_OUTBOUND_ID entry in the .env file."""
    lines = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()
    key = "PEARL_OUTBOUND_ID"
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(key + "="):
            new_lines.append(f"{key}={outbound_id}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={outbound_id}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    logger.info(f"✅ Guardado {key} en {ENV_FILE}")


def choose_campaign(campaigns):
    print("\nLista de campañas disponibles:")
    for idx, c in enumerate(campaigns, 1):
        print(f"[{idx}] {c.get('name')} — {c.get('id')}")
    while True:
        sel = input("Selecciona el número de la campaña a usar como default: ")
        try:
            idx = int(sel.strip())
            if 1 <= idx <= len(campaigns):
                return campaigns[idx - 1]
        except ValueError:
            pass
        print("Opción inválida. Intenta de nuevo.")


def main():
    name_filter: Optional[str] = None
    if len(sys.argv) > 1:
        name_filter = sys.argv[1]
    try:
        client = PearlCaller()
        campaigns = client.get_outbound_campaigns()
    except PearlAPIError as e:
        logger.error(f"No se pudo conectar a Pearl AI: {e}")
        sys.exit(1)

    chosen = None
    if name_filter:
        for c in campaigns:
            if name_filter.lower() in c.get("name", "").lower():
                chosen = c
                break
        if not chosen:
            logger.warning(f"No se encontró campaña que contenga '{name_filter}'. Se mostrará lista.")
    if not chosen:
        chosen = choose_campaign(campaigns)

    outbound_id = chosen.get("id") or chosen.get("outbound_id")
    if not outbound_id:
        logger.error("La campaña seleccionada no tiene 'id' disponible.")
        sys.exit(1)

    update_env(outbound_id)
    logger.info(f"La campaña '{chosen.get('name')}' se configuró como default.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script para descargar grabaciones de llamadas de leads interesados
Usa los datos del archivo Excel existente y nombra los archivos con el nombre de la persona
"""

import sys
import os
import requests
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import re
from urllib.parse import urlparse

# Cargar variables de entorno
load_dotenv()

def get_railway_connection():
    """Conexión directa a Railway"""
    config = {
        'host': 'ballast.proxy.rlwy.net',
        'port': 11616,
        'user': 'root',
        'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        'database': 'railway',
        'ssl_disabled': True,
        'autocommit': True,
        'charset': 'utf8mb4'
    }

    try:
        conn = mysql.connector.connect(**config)
        return conn
    except Exception as e:
        print(f"Error conectando a Railway: {e}")
        return None

def clean_filename(name):
    """Limpia el nombre para uso como nombre de archivo"""
    if not name:
        return "SIN_NOMBRE"

    # Remover caracteres especiales y espacios
    clean_name = re.sub(r'[^\w\s-]', '', name)
    clean_name = re.sub(r'\s+', '_', clean_name)
    return clean_name.upper()

def get_grabaciones_data():
    """Obtiene datos de leads con call_id para obtener grabaciones desde Pearl AI"""
    try:
        conn = get_railway_connection()
        if conn is None:
            return []

        cursor = conn.cursor()

        # Consulta para obtener call_ids de leads interesados sin cita (solo más reciente por lead)
        query = """
        SELECT l.id, l.nombre, l.apellidos, l.telefono, pc.call_id, pc.created_at
        FROM leads l
        INNER JOIN (
            SELECT lead_id, call_id, created_at,
                   ROW_NUMBER() OVER (PARTITION BY lead_id ORDER BY created_at DESC) as rn
            FROM pearl_calls
            WHERE call_id IS NOT NULL
            AND call_id != ''
            AND summary IS NOT NULL
            AND summary != ''
            AND summary != 'Call_id invalido - no reconocido por Pearl AI'
        ) pc ON l.id = pc.lead_id AND pc.rn = 1
        WHERE l.fecha_minima_reserva IS NOT NULL
        AND l.cita IS NULL
        ORDER BY l.nombre
        """

        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    except Exception as e:
        print(f"Error obteniendo datos de grabaciones: {e}")
        return []

def get_pearl_recording_url(call_id):
    """Obtiene la URL de grabación desde Pearl AI"""
    try:
        from pearl_caller import get_pearl_client

        pearl_client = get_pearl_client()
        call_details = pearl_client.get_call_status(call_id)

        if call_details and 'recording' in call_details:
            return call_details['recording']

        return None

    except Exception as e:
        print(f"  Error obteniendo URL desde Pearl AI: {e}")
        return None

def download_recording(url, filename, max_retries=3):
    """Descarga una grabación desde la URL"""
    for attempt in range(max_retries):
        try:
            print(f"  Descargando intento {attempt + 1}/{max_retries}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()

            # Obtener extensión del archivo desde la URL o usar .mp3 por defecto
            parsed_url = urlparse(url)
            ext = '.mp3'  # Por defecto
            if parsed_url.path:
                _, file_ext = os.path.splitext(parsed_url.path)
                if file_ext:
                    ext = file_ext

            full_filename = f"{filename}{ext}"

            with open(full_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(full_filename)
            print(f"  OK - Descargado: {full_filename} ({file_size} bytes)")
            return True

        except Exception as e:
            print(f"  ERROR intento {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"  Reintentando...")

    return False

def main():
    print("DESCARGA DE GRABACIONES - LEADS INTERESADOS SIN CITA")
    print("=" * 60)

    # Crear carpeta para grabaciones
    recordings_dir = "grabaciones_leads_interesados"
    if not os.path.exists(recordings_dir):
        os.makedirs(recordings_dir)
        print(f"Creada carpeta: {recordings_dir}")

    # Obtener datos de grabaciones
    print("\nObteniendo datos de grabaciones...")
    grabaciones_data = get_grabaciones_data()

    if not grabaciones_data:
        print("No se encontraron grabaciones para descargar.")
        return

    print(f"Encontradas {len(grabaciones_data)} grabaciones")
    print("-" * 60)

    downloaded_count = 0
    failed_count = 0
    processed_leads = set()

    for row in grabaciones_data:
        lead_id, nombre, apellidos, telefono, call_id, created_at = row

        # Crear nombre de archivo
        nombre_completo = f"{nombre or 'SIN_NOMBRE'}_{apellidos or ''}".strip('_')
        clean_name = clean_filename(nombre_completo)

        # Agregar ID y teléfono para mayor identificación
        filename = f"{clean_name}_ID{lead_id}_{telefono}"
        filepath = os.path.join(recordings_dir, filename)

        print(f"\n[{downloaded_count + failed_count + 1}] {nombre_completo} (ID: {lead_id})")
        print(f"  Teléfono: {telefono}")
        print(f"  Call ID: {call_id}")
        print(f"  Fecha: {created_at}")

        # Verificar si ya existe
        existing_files = [f for f in os.listdir(recordings_dir) if f.startswith(filename)]
        if existing_files:
            print(f"  ⚠️ Ya existe: {existing_files[0]}")
            continue

        # Obtener URL de grabación desde Pearl AI
        print(f"  Obteniendo URL de grabación desde Pearl AI...")
        recording_url = get_pearl_recording_url(call_id)

        if not recording_url:
            print(f"  ERROR - No se pudo obtener URL de grabacion")
            failed_count += 1
            continue

        print(f"  URL obtenida: {recording_url[:50]}...")

        # Descargar grabación
        if download_recording(recording_url, filepath):
            downloaded_count += 1
        else:
            failed_count += 1
            print(f"  ERROR - FALLO al descargar grabacion")

    print("\n" + "=" * 60)
    print(f"RESUMEN FINAL:")
    print(f"  Grabaciones descargadas: {downloaded_count}")
    print(f"  Errores: {failed_count}")
    print(f"  Total procesadas: {downloaded_count + failed_count}")
    print(f"  Carpeta: {recordings_dir}")

if __name__ == "__main__":
    main()
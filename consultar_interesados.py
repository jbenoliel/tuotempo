#!/usr/bin/env python3
"""
Script para consultar leads interesados que aun no tienen cita asignada
"""

import sys
import os
import mysql.connector
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

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
        print("Conexión a Railway establecida correctamente")
        return conn
    except Exception as e:
        print(f"Error conectando a Railway: {e}")
        return None

def consultar_interesados_sin_cita():
    """
    Consulta leads que tienen fecha_minima_reserva (interesados)
    pero aun no tienen cita asignada
    """
    try:
        conn = get_railway_connection()
        if conn is None:
            print("Error: No se pudo conectar a la base de datos")
            return []

        cursor = conn.cursor()

        # Consultar leads interesados sin cita - incluyendo datos de llamadas
        query = """
        SELECT l.id, l.nombre, l.apellidos, l.telefono, l.telefono2, l.email,
               l.fecha_minima_reserva, l.ciudad, l.nombre_clinica,
               l.status_level_1, l.status_level_2, l.updated_at,
               l.call_time, l.call_summary, l.origen_archivo
        FROM leads l
        WHERE l.fecha_minima_reserva IS NOT NULL
        AND l.cita IS NULL
        ORDER BY l.fecha_minima_reserva ASC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print(f"LEADS INTERESADOS SIN CITA ASIGNADA: {len(results)} encontrados")
        print("=" * 80)

        if results:
            # Crear DataFrame para Excel - incluir datos de llamada
            columns = ['ID', 'Nombre', 'Apellidos', 'Telefono', 'Telefono2', 'Email',
                      'Fecha_Deseada', 'Ciudad', 'Clinica', 'Status_1', 'Status_2', 'Updated',
                      'Ultima_Llamada', 'Resumen_Llamada', 'Origen_Archivo']

            df_data = []
            for row in results:
                id_lead, nombre, apellidos, telefono, telefono2, email, fecha_min, ciudad, clinica, status1, status2, updated_at, call_time, call_summary, origen_archivo = row

                df_data.append([
                    id_lead,
                    nombre or '',
                    apellidos or '',
                    telefono or '',
                    telefono2 or '',
                    email or '',
                    fecha_min.strftime('%Y-%m-%d') if fecha_min else '',
                    ciudad or '',
                    clinica or '',
                    status1 or '',
                    status2 or '',
                    updated_at.strftime('%Y-%m-%d %H:%M') if updated_at else '',
                    call_time.strftime('%Y-%m-%d %H:%M') if call_time else '',
                    call_summary or '',
                    origen_archivo or ''
                ])

            df = pd.DataFrame(df_data, columns=columns)

            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"leads_interesados_sin_cita_{timestamp}.xlsx"

            # Guardar a Excel
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"Archivo Excel generado: {filename}")

            # Mostrar resumen en consola
            print(f"\n{'ID':<5} {'NOMBRE':<20} {'TELEFONO':<12} {'FECHA DESEADA':<12} {'ULTIMA LLAMADA':<16}")
            print("-" * 70)

            for i, row in enumerate(df_data):
                if i < 10:  # Solo primeros 10 para consola
                    print(f"{row[0]:<5} {row[1][:20]:<20} {row[3]:<12} {row[6]:<12} {row[12]:<16}")

            if len(df_data) > 10:
                print(f"... y {len(df_data) - 10} mas (ver archivo Excel completo)")
        else:
            print("No se encontraron leads interesados sin cita")

        cursor.close()
        conn.close()

        return results

    except Exception as e:
        print(f"Error consultando leads: {e}")
        return []

if __name__ == "__main__":
    consultar_interesados_sin_cita()
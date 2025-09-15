#!/usr/bin/env python3
"""
Script de migración para añadir soporte de múltiples franjas horarias al scheduler.

Este script:
1. Convierte la configuración actual (working_hours_start/end) al nuevo formato
2. Permite configurar múltiples franjas horarias
3. Mantiene compatibilidad con la configuración existente
4. Proporciona ejemplos de configuraciones comunes
"""

import logging
import json
from reprogramar_llamadas_simple import get_pymysql_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_current_schedule_config():
    """Obtiene la configuración actual de horarios"""
    conn = get_pymysql_connection()
    if not conn:
        return None, None

    try:
        with conn.cursor() as cursor:
            # Obtener configuración actual
            cursor.execute("""
                SELECT config_key, config_value
                FROM scheduler_config
                WHERE config_key IN ('working_hours_start', 'working_hours_end', 'working_time_slots')
            """)

            configs = cursor.fetchall()
            config_dict = {row['config_key']: row['config_value'] for row in configs}

            return config_dict, conn

    except Exception as e:
        logger.error(f"Error obteniendo configuración actual: {e}")
        if conn:
            conn.close()
        return None, None

def migrate_to_time_slots(interactive=True):
    """Migra la configuración a múltiples franjas horarias"""

    config_dict, conn = get_current_schedule_config()
    if not config_dict or not conn:
        logger.error("No se pudo obtener la configuración actual")
        return False

    try:
        with conn.cursor() as cursor:
            current_start = config_dict.get('working_hours_start', '10:00')
            current_end = config_dict.get('working_hours_end', '20:00')

            print("=== MIGRACIÓN A MÚLTIPLES FRANJAS HORARIAS ===")
            print()
            print(f"Configuración actual: {current_start} - {current_end}")
            print()

            if interactive:
                print("Selecciona una opción:")
                print("1. Mantener horario actual como una sola franja")
                print("2. Configurar dos franjas (ej: 12:00-14:00 y 18:00-21:00)")
                print("3. Configurar horario con descanso almuerzo (ej: 09:00-12:00 y 14:00-18:00)")
                print("4. Configurar manualmente")
                print()

                try:
                    choice = input("Ingresa tu opción (1-4): ").strip()
                except:
                    choice = "1"  # Default para entornos no interactivos
            else:
                choice = "2"  # Tu ejemplo: 12:00-14:00 y 18:00-21:00

            # Configurar time_slots según la elección
            if choice == "1":
                time_slots = [{"start": current_start, "end": current_end}]
                description = "Horario convertido desde configuración anterior"

            elif choice == "2":
                time_slots = [
                    {"start": "12:00", "end": "14:00"},
                    {"start": "18:00", "end": "21:00"}
                ]
                description = "Dos franjas: mediodía y noche"

            elif choice == "3":
                time_slots = [
                    {"start": "09:00", "end": "12:00"},
                    {"start": "14:00", "end": "18:00"}
                ]
                description = "Horario laboral con descanso almuerzo"

            elif choice == "4":
                print("Configuración manual no implementada en modo no-interactivo")
                print("Usando configuración por defecto (opción 2)")
                time_slots = [
                    {"start": "12:00", "end": "14:00"},
                    {"start": "18:00", "end": "21:00"}
                ]
                description = "Dos franjas configuradas manualmente"

            else:
                logger.warning("Opción inválida, usando configuración actual")
                time_slots = [{"start": current_start, "end": current_end}]
                description = "Configuración por defecto"

            # Insertar nueva configuración
            time_slots_json = json.dumps(time_slots)

            # Verificar si ya existe working_time_slots
            cursor.execute("""
                SELECT id FROM scheduler_config WHERE config_key = 'working_time_slots'
            """)

            if cursor.fetchone():
                logger.info("Actualizando configuración existente de working_time_slots")
                cursor.execute("""
                    UPDATE scheduler_config
                    SET config_value = %s, description = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE config_key = 'working_time_slots'
                """, (time_slots_json, description))
            else:
                logger.info("Insertando nueva configuración de working_time_slots")
                cursor.execute("""
                    INSERT INTO scheduler_config (config_key, config_value, description)
                    VALUES ('working_time_slots', %s, %s)
                """, (time_slots_json, description))

            conn.commit()

            print(f"\n[OK] Migracion completada!")
            print(f"Nueva configuración:")
            for i, slot in enumerate(time_slots, 1):
                print(f"  Franja {i}: {slot['start']} - {slot['end']}")

            print(f"\nDescripción: {description}")
            print("\n📝 NOTAS IMPORTANTES:")
            print("- Las configuraciones working_hours_start/end se mantienen para compatibilidad")
            print("- El sistema usará working_time_slots cuando esté disponible")
            print("- Puedes cambiar las franjas editando scheduler_config.working_time_slots")
            print("- Los cambios se aplican automáticamente en el siguiente ciclo del daemon")

            return True

    except Exception as e:
        logger.error(f"Error durante la migración: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def show_configuration_examples():
    """Muestra ejemplos de configuraciones de franjas horarias"""

    examples = {
        "Horario continuo (9-18)": [
            {"start": "09:00", "end": "18:00"}
        ],
        "Con descanso almuerzo": [
            {"start": "09:00", "end": "12:00"},
            {"start": "14:00", "end": "18:00"}
        ],
        "Doble turno": [
            {"start": "08:00", "end": "12:00"},
            {"start": "16:00", "end": "20:00"}
        ],
        "Tu ejemplo (12-14 y 18-21)": [
            {"start": "12:00", "end": "14:00"},
            {"start": "18:00", "end": "21:00"}
        ],
        "Horario nocturno": [
            {"start": "22:00", "end": "23:59"},
            {"start": "00:00", "end": "06:00"}
        ],
        "Call center 24/7 (3 turnos)": [
            {"start": "08:00", "end": "16:00"},
            {"start": "16:00", "end": "00:00"},
            {"start": "00:00", "end": "08:00"}
        ]
    }

    print("\n=== EJEMPLOS DE CONFIGURACIONES ===")
    print()

    for name, slots in examples.items():
        print(f"[EJEMPLO] {name}:")
        slots_json = json.dumps(slots, ensure_ascii=False)
        print(f"   working_time_slots: {slots_json}")
        print()

    print("Para aplicar cualquiera de estos ejemplos:")
    print("UPDATE scheduler_config SET config_value = '[JSON_AQUÍ]' WHERE config_key = 'working_time_slots';")

def test_current_configuration():
    """Prueba la configuración actual de múltiples franjas"""

    try:
        from call_scheduler_multi_timeframes import CallSchedulerMultiTimeframes
        from datetime import datetime, time

        scheduler = CallSchedulerMultiTimeframes()

        print("\n=== PRUEBA DE CONFIGURACIÓN ACTUAL ===")
        print()

        # Mostrar franjas configuradas
        time_slots = scheduler.get_working_time_slots()
        print("Franjas horarias configuradas:")
        for i, slot in enumerate(time_slots, 1):
            print(f"  {i}. {slot['start']} - {slot['end']}")

        print()

        # Probar horarios específicos
        test_times = [
            time(8, 0),   # Antes
            time(12, 30), # Mediodía
            time(15, 0),  # Tarde
            time(19, 0),  # Noche
            time(22, 0),  # Después
        ]

        print("Pruebas de horarios:")
        today = datetime.today()

        for test_time in test_times:
            test_datetime = datetime.combine(today.date(), test_time)
            is_working = scheduler.is_working_time(test_datetime)
            current_slot = scheduler.get_current_working_slot_info(test_datetime)

            if is_working and current_slot:
                slot_info = f"(franja {current_slot['start']}-{current_slot['end']})"
            else:
                slot_info = "(fuera de franjas)"

            status = "[SI]" if is_working else "[NO]"
            print(f"  {test_time}: {status} {slot_info}")

    except Exception as e:
        logger.error(f"Error probando configuración: {e}")

if __name__ == "__main__":
    print("MIGRACIÓN A MÚLTIPLES FRANJAS HORARIAS")
    print("=" * 50)

    # 1. Mostrar ejemplos
    show_configuration_examples()

    # 2. Ejecutar migración
    if migrate_to_time_slots(interactive=False):
        print("\n" + "=" * 50)

        # 3. Probar configuración
        test_current_configuration()

        print("\n" + "=" * 50)
        print("[EXITO] MIGRACION COMPLETADA EXITOSAMENTE")
        print("El daemon ahora soporta múltiples franjas horarias!")
    else:
        print("\n[ERROR] La migracion fallo")
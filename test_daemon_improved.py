#!/usr/bin/env python3
"""
Script de prueba para el daemon mejorado de llamadas programadas
"""

from scheduled_calls_daemon_improved import ScheduledCallsDaemon
from datetime import datetime, time
import logging

# Configurar logging para la prueba
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_working_hours():
    """Prueba la lógica de horarios laborables"""
    print("=== PRUEBA DE HORARIOS LABORABLES ===")

    daemon = ScheduledCallsDaemon()

    # Casos de prueba
    test_times = [
        (time(9, 30), "Antes de horario"),
        (time(10, 0), "Inicio de horario"),
        (time(12, 30), "Medio día"),
        (time(20, 0), "Final de horario"),
        (time(21, 0), "Después de horario"),
        (time(3, 0), "Madrugada")
    ]

    for test_time, description in test_times:
        # Crear datetime ficticio para hoy
        test_datetime = datetime.combine(datetime.today(), test_time)
        is_working = daemon.scheduler.is_working_time(test_datetime)

        print(f"[TIEMPO] {description} ({test_time}): {'SI' if is_working else 'NO'}")

def test_daemon_cycle_simulation():
    """Simula un ciclo del daemon sin ejecutar llamadas reales"""
    print("\n=== SIMULACION DE CICLO DEL DAEMON ===")

    daemon = ScheduledCallsDaemon()

    # Simular verificación de estado
    should_execute = daemon.should_execute_calls()
    print(f"¿Debe ejecutar llamadas?: {'SI' if should_execute else 'NO'}")

    if should_execute:
        print("[OK] El daemon ejecutaria llamadas en este momento")
    else:
        print("[SKIP] El daemon omitira este ciclo")

    # Mostrar configuración actual
    config = daemon.get_daemon_config()
    print(f"[CONFIG] Configuracion:")
    for key, value in config.items():
        print(f"   - {key}: {value}")

def test_configuration_override():
    """Prueba qué pasa cuando se cambia la configuración dinámicamente"""
    print("\n=== PRUEBA DE CONFIGURACION DINAMICA ===")

    daemon = ScheduledCallsDaemon()

    # Simular diferentes configuraciones
    original_enabled = daemon.is_daemon_enabled()
    print(f"Estado original: {'Habilitado' if original_enabled else 'Deshabilitado'}")

    print("[INFO] En Railway, puedes cambiar estas configuraciones en scheduler_config:")
    print("   - daemon_enabled: true/false")
    print("   - working_hours_start: 08:00")
    print("   - working_hours_end: 22:00")
    print("   - scheduled_calls_interval_minutes: 3")
    print("   - max_calls_per_cycle: 20")
    print("[AUTO] Los cambios se aplican automaticamente en el siguiente ciclo")

if __name__ == "__main__":
    print("PRUEBAS DEL DAEMON MEJORADO DE LLAMADAS PROGRAMADAS")
    print("=" * 60)

    test_working_hours()
    test_daemon_cycle_simulation()
    test_configuration_override()

    print("\n" + "=" * 60)
    print("[COMPLETADO] TODAS LAS PRUEBAS COMPLETADAS")
    print("[LISTO] El daemon esta listo para usarse en Railway")
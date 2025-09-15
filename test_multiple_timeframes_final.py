#!/usr/bin/env python3
"""
Prueba final del sistema de múltiples franjas horarias
Demuestra que funciona correctamente con tu ejemplo: 12:00-14:00 y 18:00-21:00
"""

from call_scheduler_multi_timeframes import CallSchedulerMultiTimeframes
from datetime import datetime, time

def test_multiple_timeframes():
    print("=== PRUEBA FINAL DE MÚLTIPLES FRANJAS HORARIAS ===")
    print()

    # Crear scheduler y forzar tu configuración
    scheduler = CallSchedulerMultiTimeframes()

    # Configurar manualmente para la prueba (tu ejemplo)
    scheduler.config['working_time_slots'] = [
        {'start': '12:00', 'end': '14:00'},  # Primera franja: mediodía
        {'start': '18:00', 'end': '21:00'}   # Segunda franja: noche
    ]
    scheduler._config_loaded = True

    print("Configuración de prueba aplicada:")
    time_slots = scheduler.get_working_time_slots()
    for i, slot in enumerate(time_slots, 1):
        print(f"  Franja {i}: {slot['start']} - {slot['end']}")

    print()
    print("RESULTADOS DE PRUEBA:")
    print("-" * 50)

    # Casos de prueba exhaustivos
    test_cases = [
        # Antes de cualquier franja
        (time(8, 0), "Antes de franjas", False),
        (time(11, 59), "Justo antes primera franja", False),

        # Primera franja (12:00-14:00)
        (time(12, 0), "Inicio primera franja", True),
        (time(12, 30), "Medio primera franja", True),
        (time(13, 59), "Final primera franja", True),
        (time(14, 0), "Límite primera franja", True),

        # Entre franjas (14:01-17:59)
        (time(14, 1), "Justo después primera franja", False),
        (time(15, 0), "Entre franjas", False),
        (time(16, 30), "Tarde entre franjas", False),
        (time(17, 59), "Justo antes segunda franja", False),

        # Segunda franja (18:00-21:00)
        (time(18, 0), "Inicio segunda franja", True),
        (time(19, 30), "Medio segunda franja", True),
        (time(20, 59), "Final segunda franja", True),
        (time(21, 0), "Límite segunda franja", True),

        # Después de todas las franjas
        (time(21, 1), "Justo después segunda franja", False),
        (time(22, 0), "Noche", False),
        (time(23, 59), "Final del día", False),
    ]

    all_correct = True
    today = datetime.today()

    for test_time, description, expected_working in test_cases:
        test_datetime = datetime.combine(today.date(), test_time)
        is_working = scheduler.is_working_time(test_datetime)

        # Obtener información de franja si está en horario
        current_slot = scheduler.get_current_working_slot_info(test_datetime)

        if is_working and current_slot:
            slot_info = f" (franja {current_slot['start']}-{current_slot['end']})"
        else:
            slot_info = ""

        # Verificar resultado
        if is_working == expected_working:
            result = "[CORRECTO]"
        else:
            result = "[ERROR!]"
            all_correct = False

        status = "[SI]" if is_working else "[NO]"
        expected_str = "[SI]" if expected_working else "[NO]"

        print(f"{test_time} {description}:")
        print(f"    Resultado: {status}{slot_info}")
        print(f"    Esperado:  {expected_str}")
        print(f"    Estado:    {result}")
        print()

    print("=" * 50)
    if all_correct:
        print("[ÉXITO] Todas las pruebas pasaron correctamente!")
        print("El sistema de múltiples franjas horarias funciona perfectamente.")
    else:
        print("[FALLO] Algunas pruebas fallaron.")

    print()
    print("CÓMO APLICAR ESTA CONFIGURACIÓN EN RAILWAY:")
    print("UPDATE scheduler_config SET config_value = '[{\"start\": \"12:00\", \"end\": \"14:00\"}, {\"start\": \"18:00\", \"end\": \"21:00\"}]' WHERE config_key = 'working_time_slots';")

    return all_correct

def test_next_slot_calculation():
    """Prueba el cálculo del siguiente slot disponible"""
    print("\n=== PRUEBA DE CÁLCULO DE PRÓXIMO SLOT ===")

    scheduler = CallSchedulerMultiTimeframes()
    scheduler.config['working_time_slots'] = [
        {'start': '12:00', 'end': '14:00'},
        {'start': '18:00', 'end': '21:00'}
    ]
    scheduler._config_loaded = True

    # Casos para encontrar próximo slot
    test_cases = [
        (time(10, 0), "Mañana antes de franjas"),
        (time(13, 0), "Durante primera franja"),
        (time(16, 0), "Entre franjas"),
        (time(20, 0), "Durante segunda franja"),
        (time(23, 0), "Después de todas las franjas"),
    ]

    today = datetime.today()

    for test_time, description in test_cases:
        test_datetime = datetime.combine(today.date(), test_time)
        next_slot = scheduler.find_next_working_slot(test_datetime)

        print(f"{test_time} ({description}):")
        print(f"    Próximo slot: {next_slot.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

if __name__ == "__main__":
    success = test_multiple_timeframes()
    test_next_slot_calculation()

    if success:
        print("\n[SISTEMA LISTO] Múltiples franjas horarias implementado correctamente!")
        print("Puedes usar tu configuración: 12:00-14:00 y 18:00-21:00")
    else:
        print("\n[NECESITA REVISIÓN] Hay problemas en la implementación.")
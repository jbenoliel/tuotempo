"""
Script para probar el parsing de nuevaCita con diferentes formatos
"""

def test_nuevacita_parsing():
    """Probar los diferentes formatos de nuevaCita"""

    test_cases = [
        "2025-10-14 09:50-10:10",  # Caso problemático actual
        "2025-10-14",  # Solo fecha
        "14/10/2025",  # Formato DD/MM/YYYY
        "2025-10-14 09:50",  # Con hora pero sin rango
        "2025-10-14 09:50:00"  # Con hora completa
    ]

    print("=== PRUEBA DE PARSING DE NUEVACITA ===")

    for fecha_str in test_cases:
        print(f"\nProbando: '{fecha_str}'")

        # Simular la lógica del código
        if '/' in fecha_str:
            # Formato DD/MM/YYYY
            dia, mes, anio = fecha_str.split('/')
            fecha_formateada = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            print(f"  Fecha (DD/MM/YYYY): {fecha_formateada}")
        else:
            # Extraer solo la fecha
            fecha_formateada = fecha_str.split(' ')[0]
            print(f"  Fecha (YYYY-MM-DD): {fecha_formateada}")

            # Extraer hora si viene
            if ' ' in fecha_str:
                try:
                    hora_parte = fecha_str.split(' ')[1]
                    if '-' in hora_parte:
                        hora_inicio = hora_parte.split('-')[0]  # "09:50"
                    else:
                        hora_inicio = hora_parte  # "09:50"

                    # Asegurar formato HH:MM:SS
                    if len(hora_inicio.split(':')) == 2:
                        hora_inicio += ':00'
                    print(f"  Hora extraída: {hora_inicio}")
                except Exception as e:
                    print(f"  Error extrayendo hora: {e}")

if __name__ == "__main__":
    test_nuevacita_parsing()
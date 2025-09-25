#!/usr/bin/env python3
"""
Correcciones finales exactas para los 31 leads huérfanos basado en análisis de outcomes
"""

import pandas as pd
from datetime import datetime

def generar_correcciones_finales():
    """Generar Excel con correcciones exactas para cada lead"""

    # Correcciones basadas en el análisis de outcomes realizado
    correcciones = [
        # Leads con 2+ Outcome 6 → "Numero erroneo"
        (2108, "Numero erroneo", "Fallo múltiple", "2 outcomes 6 (Failed)"),
        (2147, "Numero erroneo", "Fallo múltiple", "2 outcomes 6 (Failed)"),
        (2157, "Numero erroneo", "Fallo múltiple", "2 outcomes 6 (Failed)"),
        (2264, "Numero erroneo", "Fallo múltiple", "2 outcomes 6 (Failed)"),
        (2280, "Numero erroneo", "Fallo múltiple", "2 outcomes 6 (Failed)"),

        # Leads con 1 Outcome 6 → "Volver a llamar"
        (1971, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (1989, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2002, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2092, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2094, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2098, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2186, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2315, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2323, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2388, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),
        (2405, "Volver a llamar", "Fallo centralita", "1 outcome 6 (Failed)"),

        # Leads solo con no-contacto (4,5,7) → "Volver a llamar"
        (1985, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5 (ocupado,colgó)"),
        (2000, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5 (ocupado,colgó)"),
        (2005, "Volver a llamar", "buzón", "Solo outcomes 4,7 (ocupado,no contesta)"),
        (2072, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5,7 (no-contacto)"),
        (2090, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5,7 (no-contacto)"),
        (2132, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5 (ocupado,colgó)"),
        (2162, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5,7 (no-contacto)"),
        (2243, "Volver a llamar", "buzón", "Solo outcomes 4,5,7 (no-contacto)"),
        (2261, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5 (ocupado,colgó)"),
        (2273, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5 (ocupado,colgó)"),
        (2328, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5,7 (no-contacto)"),
        (2372, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5,7 (no-contacto)"),
        (2399, "Volver a llamar", "buzón", "Solo outcomes 4,7 (ocupado,no contesta)"),
        (2407, "Volver a llamar", "no disponible cliente", "Solo outcomes 4,5,7 (no-contacto)"),
        (2422, "Volver a llamar", "buzón", "Solo outcomes 4,7 (ocupado,no contesta)"),
    ]

    # Crear DataFrame
    df = pd.DataFrame(correcciones, columns=[
        'Lead_ID', 'Status_Level_1_Nuevo', 'Status_Level_2_Nuevo', 'Razón'
    ])

    # Generar Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_excel = f"correcciones_definitivas_leads_{timestamp}.xlsx"

    with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Correcciones_Definitivas', index=False)

        worksheet = writer.sheets['Correcciones_Definitivas']

        # Ajustar columnas
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 60)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

    print(f"Excel generado: {archivo_excel}")

    # Generar SQL para aplicar correcciones
    sql_file = f"correcciones_definitivas_leads_{timestamp}.sql"
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write("-- Correcciones definitivas para los 31 leads huérfanos\n")
        f.write("-- Basado en análisis de outcomes de Pearl\n")
        f.write(f"-- Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("-- Verificar antes de ejecutar:\n")
        f.write("-- SELECT id, nombre, apellidos, status_level_1, status_level_2 FROM leads WHERE id IN (\n--   ")
        f.write(','.join([str(c[0]) for c in correcciones]))
        f.write("\n-- );\n\n")

        f.write("-- Aplicar correcciones:\n")
        for lead_id, status1, status2, razon in correcciones:
            f.write(f"UPDATE leads SET status_level_1 = '{status1}', status_level_2 = '{status2}' WHERE id = {lead_id}; -- {razon}\n")

    print(f"SQL generado: {sql_file}")

    # Mostrar estadísticas
    stats = {}
    for _, status1, _, _ in correcciones:
        stats[status1] = stats.get(status1, 0) + 1

    print(f"\nEstadísticas de correcciones:")
    for status, count in stats.items():
        print(f"  {status}: {count} leads")

    print(f"\nTotal leads corregidos: {len(correcciones)}")

    return archivo_excel

if __name__ == "__main__":
    archivo = generar_correcciones_finales()
    print(f"Correcciones finales preparadas en: {archivo}")
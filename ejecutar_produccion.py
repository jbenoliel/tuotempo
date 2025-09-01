#!/usr/bin/env python3
"""
Script para ejecutar el procesador en modo PRODUCCIÓN automáticamente
"""

import sys
import os
from procesar_llamadas_segurcaixa import SegurcaixaProcessor

def main():
    print("\n" + "="*60)
    print("PROCESADOR DE LLAMADAS SEGURCAIXA -> API ACTUALIZAR_RESULTADO")
    print("="*60)
    print("MODO: PRODUCCIÓN (llamadas reales a la API)")
    
    # Archivo a procesar (con URLs de grabación y campos JSON)
    file_path = r"C:\Users\jbeno\CascadeProjects\tuotempo\Llamadas_07_30_2025_08_01_2025_procesar_grabaciones_campos_json.xlsx"
    
    print(f"\nArchivo: {file_path}")
    print("Modo: PRODUCCIÓN")
    
    # Confirmación final
    confirm = input("\nATENCION: Esto realizará llamadas REALES a la API. ¿Continuar? (s/N): ")
    if confirm.lower() != 's':
        print("Operación cancelada.")
        return
    
    # Crear procesador en modo PRODUCCIÓN (dry_run=False)
    processor = SegurcaixaProcessor(dry_run=False)
    
    print(f"\nIniciando procesamiento en PRODUCCIÓN...")
    processor.process_excel_file(file_path)
    
    print(f"\nProcesamiento completado. Ver log: procesamiento_segurcaixa.log")

if __name__ == "__main__":
    main()

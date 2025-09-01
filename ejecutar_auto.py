#!/usr/bin/env python3
"""
Script para ejecutar el procesador automáticamente en PRODUCCIÓN
"""

from procesar_llamadas_segurcaixa import SegurcaixaProcessor

def main():
    print("\n" + "="*60)
    print("PROCESADOR AUTOMÁTICO - LLAMADAS SEGURCAIXA")
    print("="*60)
    print("MODO: PRODUCCIÓN (llamadas reales a la API)")
    
    # Archivo a procesar (con URLs de grabación y campos JSON)
    file_path = r"C:\Users\jbeno\CascadeProjects\tuotempo\Llamadas_07_30_2025_08_01_2025_procesar_grabaciones_campos_json.xlsx"
    
    print(f"\nArchivo: {file_path}")
    print("Iniciando procesamiento automático...")
    
    # Crear procesador en modo PRODUCCIÓN (dry_run=False)
    processor = SegurcaixaProcessor(dry_run=False)
    
    # Ejecutar directamente
    processor.process_excel_file(file_path)
    
    print(f"\nProcesamiento completado. Ver log: procesamiento_segurcaixa.log")

if __name__ == "__main__":
    main()

import pandas as pd
import os
from datetime import datetime
import math

# Archivo de entrada y salida
archivo_entrada = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\Import leads template - prueba.xlsx"
nombre_base = os.path.basename(archivo_entrada)
nombre_sin_extension = os.path.splitext(nombre_base)[0]
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
archivo_salida = f"C:\\Users\\jbeno\\Dropbox\\TEYAME\\Prueba Segurcaixa\\{nombre_sin_extension}_intercalado_{timestamp}.xlsx"

# Lista de agentes en el orden requerido
agentes = ['Marisa', 'Pilar', 'Mayte', 'Eva']

# Leer el archivo Excel
try:
    # Leer el archivo Excel
    df = pd.read_excel(archivo_entrada)
    print(f"Archivo leído correctamente. Contiene {len(df)} filas.")
    
    # Verificar si el archivo tiene contenido
    if len(df) == 0:
        print("El archivo Excel está vacío.")
        exit(1)
        
    # Obtener el número total de filas
    total_filas = len(df)
    
    # Calcular cuántas filas por agente
    filas_por_agente = math.ceil(total_filas / len(agentes))
    print(f"\nTotal de filas: {total_filas}")
    print(f"Filas por agente (aproximadamente): {filas_por_agente}")
    
    # Dividir el dataframe en partes iguales
    partes = []
    inicio = 0
    for i in range(len(agentes)):
        fin = min(inicio + filas_por_agente, total_filas)
        if inicio < fin:  # Asegurarse de que haya filas para este agente
            parte = df.iloc[inicio:fin].reset_index(drop=True)
            partes.append(parte)
            print(f"Agente {agentes[i]}: {len(parte)} filas")
        inicio = fin
    
    # Crear el dataframe intercalado
    resultado = pd.DataFrame(columns=df.columns)
    
    # Intercalar las filas
    max_filas = max([len(parte) for parte in partes])
    
    for fila_idx in range(max_filas):
        for agente_idx, parte in enumerate(partes):
            if fila_idx < len(parte):
                resultado = pd.concat([resultado, parte.iloc[[fila_idx]]], ignore_index=True)
    
    # Guardar el archivo intercalado
    resultado.to_excel(archivo_salida, index=False)
    print(f"\n¡Archivo guardado con éxito en: {archivo_salida}!")
    
    # Mostrar resultados
    print("\nResumen del nuevo orden:")
    for i, agente in enumerate(agentes):
        print(f"{agente}: {len(partes[i])} filas")
    
    print(f"\nTotal de filas en el archivo final: {len(resultado)}")
    print("\nEl nuevo archivo tiene las filas organizadas de la siguiente manera:")
    print(f"1ª fila: Marisa, 1ª fila: Pilar, 1ª fila: Mayte, 1ª fila: Eva")
    print(f"2ª fila: Marisa, 2ª fila: Pilar, 2ª fila: Mayte, 2ª fila: Eva")
    print(f"Y así sucesivamente...")

except Exception as e:
    print(f"Error al procesar el archivo: {e}")
    import traceback
    traceback.print_exc()

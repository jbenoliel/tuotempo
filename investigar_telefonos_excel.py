"""
Investigar formato de teléfonos en Excel para corregir la búsqueda
"""

import pandas as pd

def investigar_telefonos():
    excel_path = r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\NLPearlCalls09_10_2025 00_00_00__09_10_2025 23_59_59.xlsx"
    
    try:
        df = pd.read_excel(excel_path)
        
        print("INVESTIGACION DE TELEFONOS EN EXCEL")
        print("="*50)
        print(f"Total filas: {len(df)}")
        print(f"Columnas: {list(df.columns)}")
        print()
        
        # Mostrar algunos ejemplos de la columna 'To'
        print("Primeros 10 valores de la columna 'To':")
        for i, valor in enumerate(df['To'].head(10)):
            print(f"  {i+1}. {valor}")
        
        print()
        
        # Buscar específicamente algunos teléfonos que sabemos existen
        telefonos_buscar = ['613750493', '673213075', '620925853']
        
        for telefono in telefonos_buscar:
            print(f"Buscando telefono {telefono}:")
            
            # Convertir columna 'To' a string
            df['To'] = df['To'].astype(str)
            
            # Buscar con diferentes patrones - ahora sabemos que el formato es 34XXXXXXXXX
            patterns = [
                f"34{telefono}",        # Formato exacto del Excel
                f".*34{telefono}.*",    # Con prefijo España
                f".*{telefono}.*",      # Sin prefijo
                telefono                # Teléfono solo
            ]
            
            for pattern in patterns:
                try:
                    matches = df[df['To'].str.contains(pattern, na=False, regex=True)]
                    if not matches.empty:
                        print(f"  Encontrado con patron '{pattern}': {len(matches)} resultados")
                        print(f"    Ejemplo: {matches.iloc[0]['To']}")
                        print(f"    Nombre: {matches.iloc[0].get('Name', 'N/A')}")
                        break
                except Exception as e:
                    print(f"  Error con patron '{pattern}': {e}")
            else:
                print(f"  No encontrado con ningun patron")
            
            print()
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    investigar_telefonos()
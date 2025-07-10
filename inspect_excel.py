"""Utility to inspect the test Excel file with leads/calls.
Prints sheet names, columns, and first 10 rows so we can compare with DB."""
import pandas as pd
from pathlib import Path

EXCEL_PATH = Path(r"C:\Users\jbeno\Dropbox\TEYAME\Prueba Segurcaixa\data de prueba callsPearl.xlsx")

if not EXCEL_PATH.exists():
    raise SystemExit(f"Excel file not found: {EXCEL_PATH}")

xl = pd.ExcelFile(EXCEL_PATH)
print("Sheets:", xl.sheet_names)

for sheet in xl.sheet_names:
    print("\n=== Sheet:", sheet, "===")
    df = xl.parse(sheet)
    print("Columns:", list(df.columns))
    print(df.head(10))

# 🏥 Buscador de areaId para Excel

Este programa te permite encontrar automáticamente los `areaId` de clínicas basándose en el nombre y/o dirección desde un archivo Excel.

## 🚀 Uso Rápido

### Opción 1: Uso Interactivo (Recomendado)
```bash
python ejemplo_buscar_areaid.py
```
Este script te guiará paso a paso para configurar la búsqueda.

### Opción 2: Uso Directo
```bash
python buscar_areaid_excel.py --excel "archivo.xlsx" --nombre "NOMBRE_CLINICA" --direccion "DIRECCION_CLINICA"
```

## 📋 Ejemplos Comunes

### Para archivos de Segurcaixa típicos:
```bash
python buscar_areaid_excel.py --excel "clinicas_segurcaixa.xlsx" --nombre "NOMBRE_CLINICA" --direccion "DIRECCION_CLINICA"
```

### Solo por nombre de clínica:
```bash
python buscar_areaid_excel.py --excel "clinicas.xlsx" --nombre "CLINICA"
```

### Solo por dirección:
```bash
python buscar_areaid_excel.py --excel "clinicas.xlsx" --direccion "DIRECCION"
```

### Especificar archivo de salida:
```bash
python buscar_areaid_excel.py --excel "clinicas.xlsx" --nombre "CLINICA" --output "resultado_final.xlsx"
```

## 📊 ¿Qué hace el programa?

1. **Lee tu Excel** con información de clínicas
2. **Obtiene todas las clínicas** disponibles de TuoTempo
3. **Busca coincidencias** usando:
   - Coincidencia exacta por nombre/dirección
   - Coincidencia parcial (fuzzy matching)
   - Búsqueda por palabras clave
4. **Genera un nuevo Excel** con 3 columnas adicionales:
   - `areaId`: El ID encontrado
   - `match_source`: Cómo se encontró la coincidencia
   - `match_confidence`: Nivel de confianza (0-100%)

## 📁 Estructura del Excel de Entrada

Tu Excel debe tener al menos una de estas columnas:
- **Nombre de la clínica**: `NOMBRE_CLINICA`, `Nombre`, `Centro`, `Clínica`, etc.
- **Dirección**: `DIRECCION_CLINICA`, `Dirección`, `Direccion`, etc.

Ejemplo:
| NOMBRE_CLINICA | DIRECCION_CLINICA |
|----------------|-------------------|
| Adeslas Dental Madrid | Calle Gran Vía, 45 |
| Clínica Barcelona | Avenida Diagonal, 123 |

## 📈 Resultados

El programa genera un Excel con columnas adicionales:

| NOMBRE_CLINICA | DIRECCION_CLINICA | areaId | match_source | match_confidence |
|----------------|-------------------|---------|--------------|------------------|
| Adeslas Dental Madrid | Calle Gran Vía, 45 | default@tt_adeslas_madrid_001 | dirección exacta | 100 |
| Clínica Barcelona | Avenida Diagonal, 123 | default@tt_adeslas_bcn_002 | nombre parcial | 85 |

## 🎯 Tipos de Coincidencias

- **dirección exacta** (100%): Coincidencia perfecta de dirección
- **nombre exacto** (100%): Coincidencia perfecta de nombre
- **dirección parcial** (80-90%): Coincidencia parcial de dirección
- **nombre parcial** (80-90%): Coincidencia parcial de nombre
- **palabra clave** (70%): Coincidencia por palabras del nombre
- **sin coincidencia** (0%): No se encontró coincidencia

## 🔧 Opciones Avanzadas

### Cambiar la instancia de TuoTempo:
```bash
python buscar_areaid_excel.py --excel "clinicas.xlsx" --nombre "CLINICA" --instance "tt_portal_otra_instancia"
```

### Ver todas las opciones:
```bash
python buscar_areaid_excel.py --help
```

## 📋 Requisitos

Instala las dependencias necesarias:
```bash
pip install pandas openpyxl requests fuzzywuzzy python-levenshtein
```

## 🐛 Solución de Problemas

### Error: "No se encontró el archivo"
- Verifica que la ruta del Excel sea correcta
- Usa rutas absolutas si tienes problemas

### Error: "La columna no existe"
- Verifica que el nombre de la columna sea exacto (case-sensitive)
- Lista las columnas disponibles con: `python -c "import pandas as pd; print(pd.read_excel('archivo.xlsx').columns.tolist())"`

### Pocas coincidencias encontradas
- Revisa el archivo `areas_response_TIMESTAMP.json` para ver todas las clínicas disponibles
- Considera usar solo nombre o solo dirección si una funciona mejor
- Los nombres y direcciones deben estar en español

### Error de conexión
- Verifica tu conexión a internet
- El programa necesita acceso a `app.tuotempo.com`

## 📞 Soporte

Si tienes problemas:
1. Revisa que tu Excel tenga el formato correcto
2. Verifica que las columnas existan
3. Prueba primero con un Excel pequeño (5-10 filas)
4. Revisa los archivos de log generados

## 🎉 ¡Listo!

Con estos archivos puedes procesar cualquier Excel para encontrar los `areaId` de las clínicas automáticamente.

**Archivos incluidos:**
- `buscar_areaid_excel.py` - Programa principal
- `ejemplo_buscar_areaid.py` - Uso interactivo
- `README_BUSCAR_AREAID.md` - Esta documentación

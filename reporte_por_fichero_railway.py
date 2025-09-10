#!/usr/bin/env python3
"""
Reporte detallado de leads de Railway por categorías y fichero de origen
"""

import pymysql
from datetime import datetime
import pandas as pd

# Configuración de Railway
RAILWAY_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 11616,
    'user': 'root',
    'password': 'YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
    'database': 'railway',
    'charset': 'utf8mb4'
}

def get_railway_connection():
    """Crear conexión a Railway"""
    return pymysql.connect(**RAILWAY_CONFIG)

def get_categoria_lead(status_level_1, status_level_2, call_attempts_count, max_attempts, lead_status, closure_reason):
    """Determinar categoría del lead según los criterios"""
    
    # Limpiar valores None
    status_level_1 = (status_level_1 or '').strip()
    status_level_2 = (status_level_2 or '').strip()
    call_attempts_count = call_attempts_count or 0
    
    # ÚTILES POSITIVOS
    if status_level_1 == 'Cita Agendada':
        if status_level_2 == 'Sin Pack':
            return 'Útiles Positivos', 'Cita sin pack'
        elif status_level_2 == 'Con Pack':
            return 'Útiles Positivos', 'Cita con pack'
        else:
            return 'Útiles Positivos', 'Cita agendada (otros)'
    
    # ÚTILES NEGATIVOS
    if status_level_1 == 'No Interesado':
        if status_level_2 == 'Paciente con tratamiento':
            return 'Útiles Negativos', 'Paciente tratamiento Adeslas'
        elif status_level_2 == 'Paciente con tratamiento particular':
            return 'Útiles Negativos', 'Paciente tratamiento particular'
        elif status_level_2 == 'Solicita baja póliza':
            return 'Útiles Negativos', 'Solicita baja póliza'
        elif status_level_2 == 'No da motivos':
            return 'Útiles Negativos', 'No desea informar motivo'
        else:
            return 'Útiles Negativos', 'No Interesado (otros)'
    
    if status_level_1 == 'Volver a llamar' and status_level_2 == 'Llamará cuando esté interesado':
        return 'Útiles Negativos', 'Llamará cuando esté interesado'
    
    # NO ÚTIL
    if lead_status == 'closed':
        if closure_reason == 'Teléfono erróneo':
            return 'No Útil', 'Teléfono erróneo'
        elif closure_reason == 'Ilocalizable':
            return 'No Útil', 'Ilocalizable'
        elif closure_reason == 'No colabora':
            return 'No Útil', 'No colabora'
        else:
            return 'No Útil', 'Cerrado (otros)'
    
    # Leads con máximo de intentos alcanzado
    if call_attempts_count >= max_attempts and status_level_1 == 'Volver a llamar':
        return 'No Útil', 'Máximo intentos alcanzado'
    
    # Clasificación adicional para "Volver a llamar" con subestados
    if status_level_1 == 'Volver a llamar':
        if 'no disponible' in status_level_2.lower():
            return 'No Útil', 'Ilocalizable (no disponible)'
        elif 'cortado' in status_level_2.lower():
            return 'No Útil', 'No colabora (cortado)'
        elif 'buzón' in status_level_2.lower():
            return 'No Útil', 'Ilocalizable (buzón)'
        else:
            return 'Volver a llamar', status_level_2 or 'Sin especificar'
    
    # Sin procesar
    if not status_level_1:
        return 'Sin procesar', 'Sin procesar'
    
    # Otros casos
    return 'Otros', f'{status_level_1} | {status_level_2}'

def generar_reporte_por_fichero():
    """Generar reporte detallado por categorías y fichero de origen"""
    
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("REPORTE DETALLADO POR FICHERO DE ORIGEN - RAILWAY")
    print("=" * 60)
    
    # Obtener configuración de límite de intentos
    cursor.execute("SELECT config_value FROM scheduler_config WHERE config_key = 'max_attempts'")
    max_attempts_result = cursor.fetchone()
    max_attempts = int(max_attempts_result[0]) if max_attempts_result else 6
    print(f"Limite maximo de intentos configurado: {max_attempts}")
    print()
    
    # Obtener todos los leads con datos completos
    cursor.execute("""
        SELECT 
            IFNULL(origen_archivo, 'Sin origen') as fichero_origen,
            status_level_1,
            status_level_2, 
            call_attempts_count,
            lead_status,
            closure_reason,
            COUNT(*) as cantidad
        FROM leads
        GROUP BY origen_archivo, status_level_1, status_level_2, 
                 call_attempts_count, lead_status, closure_reason
        ORDER BY origen_archivo, cantidad DESC
    """)
    
    results = cursor.fetchall()
    
    # Procesar resultados
    data_table = []
    resumen_por_fichero = {}
    
    for row in results:
        fichero_origen = row[0]
        status_level_1 = row[1]
        status_level_2 = row[2]
        call_attempts_count = row[3]
        lead_status = row[4] 
        closure_reason = row[5]
        cantidad = row[6]
        
        # Determinar categoría
        categoria_principal, categoria_detalle = get_categoria_lead(
            status_level_1, status_level_2, call_attempts_count, 
            max_attempts, lead_status, closure_reason
        )
        
        # Agregar a tabla detallada
        data_table.append({
            'Fichero Origen': fichero_origen,
            'Categoria Principal': categoria_principal,
            'Categoria Detalle': categoria_detalle,
            'Status Level 1': status_level_1 or 'NULL',
            'Status Level 2': status_level_2 or 'NULL',
            'Call Attempts': call_attempts_count,
            'Lead Status': lead_status,
            'Closure Reason': closure_reason or 'NULL',
            'Cantidad': cantidad
        })
        
        # Agregar al resumen por fichero
        if fichero_origen not in resumen_por_fichero:
            resumen_por_fichero[fichero_origen] = {}
        
        key = f"{categoria_principal} - {categoria_detalle}"
        if key not in resumen_por_fichero[fichero_origen]:
            resumen_por_fichero[fichero_origen][key] = 0
        resumen_por_fichero[fichero_origen][key] += cantidad
    
    # Crear DataFrames
    df_detalle = pd.DataFrame(data_table)
    
    # Crear tabla resumen pivotada
    pivot_data = []
    todas_categorias = set()
    
    for fichero, categorias in resumen_por_fichero.items():
        for categoria in categorias.keys():
            todas_categorias.add(categoria)
    
    todas_categorias = sorted(list(todas_categorias))
    
    for fichero in resumen_por_fichero.keys():
        fila = {'Fichero Origen': fichero}
        total_fichero = 0
        for categoria in todas_categorias:
            cantidad = resumen_por_fichero[fichero].get(categoria, 0)
            fila[categoria] = cantidad
            total_fichero += cantidad
        fila['TOTAL'] = total_fichero
        pivot_data.append(fila)
    
    df_resumen = pd.DataFrame(pivot_data)
    
    # Agregar fila de totales
    fila_totales = {'Fichero Origen': 'TOTAL GENERAL'}
    for categoria in todas_categorias:
        fila_totales[categoria] = df_resumen[categoria].sum()
    fila_totales['TOTAL'] = df_resumen['TOTAL'].sum()
    
    df_resumen = pd.concat([df_resumen, pd.DataFrame([fila_totales])], ignore_index=True)
    
    # Mostrar resumen por consola
    print("RESUMEN POR FICHERO DE ORIGEN")
    print("-" * 40)
    
    for fichero in sorted(resumen_por_fichero.keys()):
        print(f"\n{fichero}:")
        total_fichero = sum(resumen_por_fichero[fichero].values())
        print(f"  Total leads: {total_fichero}")
        
        # Mostrar principales categorías
        categorias_ordenadas = sorted(resumen_por_fichero[fichero].items(), 
                                    key=lambda x: x[1], reverse=True)
        for categoria, cantidad in categorias_ordenadas[:5]:  # Top 5
            porcentaje = (cantidad / total_fichero) * 100 if total_fichero > 0 else 0
            print(f"  - {categoria}: {cantidad} ({porcentaje:.1f}%)")
        
        if len(categorias_ordenadas) > 5:
            otros_total = sum(cantidad for categoria, cantidad in categorias_ordenadas[5:])
            porcentaje_otros = (otros_total / total_fichero) * 100 if total_fichero > 0 else 0
            print(f"  - Otros: {otros_total} ({porcentaje_otros:.1f}%)")
    
    print("\n" + "=" * 60)
    
    # Exportar a Excel con múltiples hojas
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"reporte_por_fichero_railway_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Hoja 1: Resumen pivotado
        df_resumen.to_excel(writer, sheet_name='Resumen por Fichero', index=False)
        
        # Hoja 2: Detalle completo
        df_detalle.to_excel(writer, sheet_name='Detalle Completo', index=False)
        
        # Formatear las hojas
        workbook = writer.book
        
        # Formatear hoja resumen
        worksheet_resumen = writer.sheets['Resumen por Fichero']
        
        # Ajustar ancho de columnas
        for column in worksheet_resumen.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Máximo 50
            worksheet_resumen.column_dimensions[column_letter].width = adjusted_width
        
        # Formatear hoja detalle  
        worksheet_detalle = writer.sheets['Detalle Completo']
        for column in worksheet_detalle.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet_detalle.column_dimensions[column_letter].width = adjusted_width
    
    print(f"Archivo generado: {filename}")
    print(f"- Hoja 'Resumen por Fichero': Tabla pivotada con totales por categoria y fichero")
    print(f"- Hoja 'Detalle Completo': Todos los registros con clasificacion detallada")
    
    conn.close()

if __name__ == "__main__":
    generar_reporte_por_fichero()
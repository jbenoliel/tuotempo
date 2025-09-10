#!/usr/bin/env python3
"""
Reporte detallado de leads de Railway por categorías específicas
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

def generar_reporte_detallado():
    """Generar reporte detallado por categorías"""
    
    conn = get_railway_connection()
    cursor = conn.cursor()
    
    print("REPORTE DETALLADO DE LEADS - RAILWAY")
    print("=" * 50)
    
    # Obtener configuración de límite de intentos
    cursor.execute("SELECT config_value FROM scheduler_config WHERE config_key = 'max_attempts'")
    max_attempts_result = cursor.fetchone()
    max_attempts = int(max_attempts_result[0]) if max_attempts_result else 6
    print(f"Limite maximo de intentos configurado: {max_attempts}")
    print()
    
    # ===== ÚTILES POSITIVOS (ACEPTA CITA) =====
    print("UTILES POSITIVOS (Acepta Cita)")
    print("-" * 30)
    
    # Cita sin pack
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'Cita Agendada' 
        AND TRIM(status_level_2) = 'Sin Pack'
    """)
    cita_sin_pack = cursor.fetchone()[0]
    print(f"• Cita sin pack: {cita_sin_pack}")
    
    # Cita con pack
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'Cita Agendada' 
        AND TRIM(status_level_2) = 'Con Pack'
    """)
    cita_con_pack = cursor.fetchone()[0]
    print(f"• Cita con pack: {cita_con_pack}")
    
    total_utiles_positivos = cita_sin_pack + cita_con_pack
    print(f"TOTAL ÚTILES POSITIVOS: {total_utiles_positivos}")
    print()
    
    # ===== ÚTILES NEGATIVOS (NO ACEPTA CITA) =====
    print("UTILES NEGATIVOS (No acepta cita)")
    print("-" * 30)
    
    # Paciente habitual/Tratamiento en curso en Adeslas
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'No Interesado' 
        AND TRIM(status_level_2) = 'Paciente con tratamiento'
    """)
    paciente_tratamiento_adeslas = cursor.fetchone()[0]
    print(f"• Paciente habitual/Tratamiento en curso en Adeslas: {paciente_tratamiento_adeslas}")
    
    # Paciente con tratamiento en curso particular
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'No Interesado' 
        AND TRIM(status_level_2) = 'Paciente con tratamiento particular'
    """)
    paciente_tratamiento_particular = cursor.fetchone()[0]
    print(f"• Paciente con tratamiento en curso particular: {paciente_tratamiento_particular}")
    
    # Llamará cuando esté interesado
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'Volver a llamar' 
        AND TRIM(status_level_2) = 'Llamará cuando esté interesado'
    """)
    llamara_cuando_interesado = cursor.fetchone()[0]
    print(f"• Llamará cuando esté interesado: {llamara_cuando_interesado}")
    
    # Solicitan baja póliza
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'No Interesado' 
        AND TRIM(status_level_2) = 'Solicita baja póliza'
    """)
    solicita_baja_poliza = cursor.fetchone()[0]
    print(f"• Solicitan baja póliza: {solicita_baja_poliza}")
    
    # No desea informar motivo
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE TRIM(status_level_1) = 'No Interesado' 
        AND TRIM(status_level_2) = 'No da motivos'
    """)
    no_da_motivos = cursor.fetchone()[0]
    print(f"• No desea informar motivo: {no_da_motivos}")
    
    total_utiles_negativos = (paciente_tratamiento_adeslas + paciente_tratamiento_particular + 
                             llamara_cuando_interesado + solicita_baja_poliza + no_da_motivos)
    print(f"TOTAL ÚTILES NEGATIVOS: {total_utiles_negativos}")
    print()
    
    # ===== NO ÚTIL =====
    print("NO UTIL")
    print("-" * 30)
    
    # Teléfono erróneo
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE lead_status = 'closed' 
        AND closure_reason = 'Teléfono erróneo'
    """)
    telefono_erroneo = cursor.fetchone()[0]
    print(f"• Teléfono erróneo: {telefono_erroneo}")
    
    # Ilocalizable (incluir cerrados por máximo de intentos)
    cursor.execute(f"""
        SELECT COUNT(*) FROM leads 
        WHERE (lead_status = 'closed' AND closure_reason = 'Ilocalizable')
        OR (call_attempts_count >= {max_attempts} AND status_level_1 = 'Volver a llamar')
    """)
    ilocalizable = cursor.fetchone()[0]
    print(f"• Ilocalizable (incluir cerrados por máximo de intentos): {ilocalizable}")
    
    # No colabora
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE lead_status = 'closed' 
        AND closure_reason = 'No colabora'
    """)
    no_colabora = cursor.fetchone()[0]
    print(f"• No colabora: {no_colabora}")
    
    total_no_util = telefono_erroneo + ilocalizable + no_colabora
    print(f"TOTAL NO ÚTIL: {total_no_util}")
    print()
    
    # ===== RESUMEN GENERAL =====
    print("RESUMEN GENERAL")
    print("-" * 30)
    
    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status_level_1 IS NOT NULL")
    leads_procesados = cursor.fetchone()[0]
    
    leads_sin_procesar = total_leads - leads_procesados
    
    print(f"• Total leads: {total_leads}")
    print(f"• Leads procesados: {leads_procesados}")
    print(f"• Leads sin procesar: {leads_sin_procesar}")
    print(f"• Útiles positivos: {total_utiles_positivos}")
    print(f"• Útiles negativos: {total_utiles_negativos}")
    print(f"• No útil: {total_no_util}")
    print()
    
    # Verificación: el total debería coincidir
    total_categorizado = total_utiles_positivos + total_utiles_negativos + total_no_util + leads_sin_procesar
    print(f"Verificación total: {total_categorizado} (debería ser {total_leads})")
    
    if total_categorizado != total_leads:
        diferencia = total_leads - total_categorizado
        print(f"HAY DIFERENCIA: {diferencia} leads no categorizados")
        
        # Buscar leads no categorizados
        print("\nBUSCANDO LEADS NO CATEGORIZADOS...")
        cursor.execute("""
            SELECT DISTINCT 
                CONCAT(IFNULL(status_level_1, 'NULL'), ' | ', IFNULL(status_level_2, 'NULL')) as estado_completo,
                COUNT(*) as count
            FROM leads 
            GROUP BY status_level_1, status_level_2 
            ORDER BY count DESC
            LIMIT 15
        """)
        
        print("\nTodos los estados encontrados:")
        for row in cursor.fetchall():
            print(f"  • {row[0]}: {row[1]}")
    
    print("\n" + "=" * 50)
    
    # ===== EXPORTAR A EXCEL =====
    print("Generando archivo Excel...")
    
    # Crear DataFrame con el resumen
    data = {
        'Categoría': [
            'Cita sin pack',
            'Cita con pack', 
            'Paciente tratamiento Adeslas',
            'Paciente tratamiento particular',
            'Llamará cuando interesado',
            'Solicita baja póliza',
            'No da motivos',
            'Teléfono erróneo',
            'Ilocalizable (+ máx intentos)',
            'No colabora',
            'Sin procesar'
        ],
        'Cantidad': [
            cita_sin_pack,
            cita_con_pack,
            paciente_tratamiento_adeslas,
            paciente_tratamiento_particular,
            llamara_cuando_interesado,
            solicita_baja_poliza,
            no_da_motivos,
            telefono_erroneo,
            ilocalizable,
            no_colabora,
            leads_sin_procesar
        ],
        'Tipo': [
            'Útiles Positivos',
            'Útiles Positivos',
            'Útiles Negativos',
            'Útiles Negativos', 
            'Útiles Negativos',
            'Útiles Negativos',
            'Útiles Negativos',
            'No Útil',
            'No Útil',
            'No Útil',
            'Sin Procesar'
        ]
    }
    
    df = pd.DataFrame(data)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"reporte_detallado_railway_{timestamp}.xlsx"
    
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"Archivo generado: {filename}")
    
    conn.close()

if __name__ == "__main__":
    generar_reporte_detallado()
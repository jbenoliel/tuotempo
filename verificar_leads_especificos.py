"""
Verificar el estado de leads específicos en la BD
"""

import mysql.connector
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_connection():
    return mysql.connector.connect(
        host='ballast.proxy.rlwy.net',
        port=11616,
        user='root',
        password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
        database='railway'
    )

def verificar_leads_especificos():
    conn = get_railway_connection()
    if not conn:
        logger.error("No se pudo conectar a Railway")
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Lista de nombres a buscar
        nombres_buscar = [
            "YENDERSON DEIVIS CHIRINOS VERA",
            "MANUEL PANPLONA NAVARRO", 
            "JOSEFA DIVOLS RUIZ",
            "JAUME ROBLES PALAU",
            "MARYLIN ROMAIN BURDET",
            "DARISELA CANARIO FELIZ",
            "FELIX LOPEZ MUNDEJAR",  # Note: tienes MUNDEJAR, en BD está MONDEJAR
            "LUIS PABLO VALENCIANO ROZALEN",
            "KATIA SAUDITH PEREZ FUENTES"
        ]
        
        print("VERIFICACION DE LEADS ESPECIFICOS")
        print("="*70)
        
        for nombre_completo in nombres_buscar:
            # Separar nombre y apellidos
            partes = nombre_completo.split()
            if len(partes) >= 2:
                nombre = partes[0]
                apellidos = " ".join(partes[1:])
            else:
                nombre = nombre_completo
                apellidos = ""
            
            print(f"\nBuscando: {nombre_completo}")
            
            # Buscar por nombre y apellidos exactos
            cursor.execute("""
                SELECT 
                    id, nombre, apellidos, telefono, email, nombre_clinica,
                    status_level_1, status_level_2, call_status,
                    call_attempts_count, last_call_attempt, updated_at
                FROM leads 
                WHERE CONCAT(UPPER(nombre), ' ', UPPER(apellidos)) LIKE %s
                OR UPPER(nombre) = %s
                OR CONCAT(UPPER(nombre), ' ', UPPER(apellidos)) = %s
                ORDER BY updated_at DESC
                LIMIT 3
            """, (f"%{nombre_completo.upper()}%", nombre.upper(), nombre_completo.upper()))
            
            results = cursor.fetchall()
            
            if results:
                for lead in results:
                    nombre_bd = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}".strip()
                    print(f"  ✓ ENCONTRADO - ID: {lead['id']}")
                    print(f"    Nombre BD: {nombre_bd}")
                    print(f"    Telefono: {lead.get('telefono', 'N/A')}")
                    print(f"    Clinica: {lead.get('nombre_clinica', 'N/A')}")
                    print(f"    Status L1: {lead.get('status_level_1', 'N/A')}")
                    print(f"    Status L2: {lead.get('status_level_2', 'N/A')}")
                    print(f"    Call Status: {lead.get('call_status', 'N/A')}")
                    print(f"    Intentos: {lead.get('call_attempts_count', 0)}")
                    print(f"    Ultima llamada: {lead.get('last_call_attempt', 'N/A')}")
                    print(f"    Actualizado: {lead.get('updated_at', 'N/A')}")
                    print()
            else:
                print(f"  ✗ NO ENCONTRADO")
                
                # Buscar solo por nombre si no encontramos exacto
                cursor.execute("""
                    SELECT 
                        id, nombre, apellidos, telefono, status_level_1, status_level_2
                    FROM leads 
                    WHERE UPPER(nombre) LIKE %s
                    LIMIT 3
                """, (f"%{nombre.upper()}%",))
                
                partial_results = cursor.fetchall()
                if partial_results:
                    print(f"    Coincidencias parciales:")
                    for lead in partial_results:
                        nombre_bd = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}".strip()
                        print(f"      - ID {lead['id']}: {nombre_bd} ({lead.get('status_level_1', 'N/A')})")
        
        # Buscar variante conocida FELIX LOPEZ MONDEJAR
        print(f"\n" + "="*70)
        print("BUSCANDO FELIX LOPEZ MONDEJAR (variante conocida):")
        cursor.execute("""
            SELECT 
                id, nombre, apellidos, telefono, email, nombre_clinica,
                status_level_1, status_level_2, call_status,
                call_attempts_count, last_call_attempt, updated_at
            FROM leads 
            WHERE UPPER(nombre) = 'FELIX' 
            AND UPPER(apellidos) LIKE '%LOPEZ%'
            AND UPPER(apellidos) LIKE '%MONDEJAR%'
        """)
        
        felix_result = cursor.fetchall()
        if felix_result:
            for lead in felix_result:
                nombre_bd = f"{lead.get('nombre', '')} {lead.get('apellidos', '')}".strip()
                print(f"  ✓ ENCONTRADO - ID: {lead['id']}")
                print(f"    Nombre BD: {nombre_bd}")
                print(f"    Status L1: {lead.get('status_level_1', 'N/A')}")
                print(f"    Status L2: {lead.get('status_level_2', 'N/A')}")
                print(f"    Actualizado: {lead.get('updated_at', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verificar_leads_especificos()
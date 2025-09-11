"""
Test final para verificar la lógica conPack corregida
"""

import requests
import json

def test_final_conpack():
    url = "https://tuotempo-apis-production.up.railway.app/api/actualizar_resultado"
    
    # Test con YENDERSON (que ya sabemos que existe)
    # SIN conPack=true -> debe ser "Sin Pack"
    test_sin_pack = {
        "telefono": "673213075",
        "firstName": "YENDERSON",
        "lastName": "CHIRINOS VERA",
        "fechaDeseada": "26-09-2025",
        "preferenciaMT": "morning",
        "callResult": "Cita agendada"
        # NO incluye conPack
    }
    
    print("TEST FINAL - LÓGICA CONPACK")
    print("="*40)
    print("Probando con YENDERSON (SIN conPack=true)")
    print("Debería marcar como 'Sin Pack'")
    print()
    print("Datos enviados:")
    print(json.dumps(test_sin_pack, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=test_sin_pack, timeout=30)
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\nAPI exitosa - Verificando en BD...")
            
            # Verificar resultado
            import mysql.connector
            conn = mysql.connector.connect(
                host='ballast.proxy.rlwy.net',
                port=11616,
                user='root',
                password='YUpuOBaMqUdztuRwDvZBNsRQsucGMYur',
                database='railway'
            )
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT status_level_1, status_level_2, updated_at
                FROM leads 
                WHERE telefono = '673213075'
            """)
            
            result = cursor.fetchone()
            if result:
                print(f"Status L1: {result['status_level_1']}")
                print(f"Status L2: {result['status_level_2']}")
                print(f"Actualizado: {result['updated_at']}")
                
                if result['status_level_2'] == 'Sin Pack':
                    print("\n✅ SUCCESS - Correctamente marcado como 'Sin Pack'")
                elif result['status_level_2'] == 'Con Pack':
                    print("\n❌ ERROR - Incorrectamente marcado como 'Con Pack'")
                else:
                    print(f"\n⚠️ INESPERADO - Status L2: {result['status_level_2']}")
            
            conn.close()
        else:
            print(f"Error API: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_final_conpack()
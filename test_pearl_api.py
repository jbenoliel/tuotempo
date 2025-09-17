#!/usr/bin/env python3
"""
Script para probar qué devuelve la API de Pearl AI
"""

from pearl_caller import get_pearl_client
import json

def test_pearl_api():
    """Probar llamada a la API de Pearl AI"""
    try:
        pearl_client = get_pearl_client()

        # Probar con un call_id específico
        test_call_id = "68c03ae28a2fc8e5ce02664f"  # AARON
        print(f"Probando API con call_id: {test_call_id}")

        call_details = pearl_client.get_call_status(test_call_id)

        print(f"\nRespuesta de Pearl AI:")
        print(json.dumps(call_details, indent=2, ensure_ascii=False))

        if call_details:
            print(f"\nCampos disponibles:")
            for key in call_details.keys():
                print(f"  - {key}: {type(call_details[key])}")

            # Buscar campos relacionados con grabación
            recording_fields = []
            for key in call_details.keys():
                if 'record' in key.lower() or 'url' in key.lower() or 'audio' in key.lower():
                    recording_fields.append(key)

            if recording_fields:
                print(f"\nCampos relacionados con grabación:")
                for field in recording_fields:
                    print(f"  - {field}: {call_details[field]}")
            else:
                print(f"\nNo se encontraron campos relacionados con grabación")

        else:
            print("No se obtuvo respuesta de Pearl AI")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pearl_api()
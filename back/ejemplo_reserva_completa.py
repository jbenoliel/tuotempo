import json
from datetime import datetime, timedelta
from tuotempo_api import TuoTempoAPI
from tuotempo_reservation import crear_reserva, convertir_formato_fecha

def ejemplo_flujo_completo():
    """
    Ejemplo de flujo completo para crear una reserva en TuoTempo:
    1. Inicializar el cliente API
    2. Buscar centros disponibles
    3. Buscar disponibilidad en un centro
    4. Crear una reserva con los datos obtenidos
    """
    # 1. Inicializar cliente API
    api = TuoTempoAPI()
    
    # 2. Buscar centros (clínicas)
    print("Buscando centros disponibles...")
    centros = api.get_centers()
    
    if not centros or len(centros) == 0:
        print("No se encontraron centros disponibles")
        return
    
    # Mostrar los primeros 3 centros
    print(f"Se encontraron {len(centros)} centros")
    for i, centro in enumerate(centros[:3]):
        print(f"  {i+1}. {centro.get('name')} (ID: {centro.get('id')})")
    
    # Seleccionar el primer centro para el ejemplo
    centro_seleccionado = centros[0]
    centro_id = centro_seleccionado.get('id')
    print(f"\nUsando centro: {centro_seleccionado.get('name')} (ID: {centro_id})")
    
    # 3. Buscar disponibilidad
    # Fechas para la búsqueda (próximos 7 días)
    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=7)
    
    fecha_inicio_str = fecha_inicio.strftime("%d/%m/%Y")
    fecha_fin_str = fecha_fin.strftime("%d/%m/%Y")
    
    print(f"\nBuscando disponibilidad del {fecha_inicio_str} al {fecha_fin_str}...")
    
    # Obtener actividades disponibles
    actividades = api.get_activities(centro_id)
    if not actividades or len(actividades) == 0:
        print("No se encontraron actividades disponibles")
        return
    
    # Seleccionar la primera actividad para el ejemplo
    actividad_seleccionada = actividades[0]
    actividad_id = actividad_seleccionada.get('id')
    print(f"Usando actividad: {actividad_seleccionada.get('name')} (ID: {actividad_id})")
    
    # Buscar disponibilidad para esta actividad
    disponibilidad = api.search_availability(
        center_id=centro_id,
        activity_id=actividad_id,
        start_date=fecha_inicio_str,
        end_date=fecha_fin_str
    )
    
    if not disponibilidad or not disponibilidad.get('availabilities'):
        print("No se encontró disponibilidad para las fechas seleccionadas")
        return
    
    # Obtener el primer hueco disponible
    primer_hueco = disponibilidad['availabilities'][0]
    print("\nPrimer hueco disponible:")
    print(f"  Fecha: {primer_hueco.get('date')}")
    print(f"  Hora inicio: {primer_hueco.get('start_time')}")
    print(f"  Hora fin: {primer_hueco.get('end_time')}")
    print(f"  Recurso: {primer_hueco.get('resource_name')} (ID: {primer_hueco.get('resource_id')})")
    print(f"  Session ID: {primer_hueco.get('provider_session_id')}")
    print(f"  Search ID: {disponibilidad.get('searchid')}")
    
    # 4. Crear usuario (si no existe)
    print("\nCreando usuario de prueba...")
    usuario = api.create_user(
        fname="Raul",
        lname="Prueba",
        phone="670252676",
        birthday="02/07/1973",
        privacy="1"
    )
    
    if not usuario or not usuario.get('memberid'):
        print("Error al crear el usuario")
        return
    
    usuario_id = usuario.get('memberid')
    print(f"Usuario creado con ID: {usuario_id}")
    
    # 5. Crear reserva con los datos obtenidos
    print("\nCreando reserva...")
    
    # Datos necesarios para la reserva según la documentación
    resultado = crear_reserva(
        userid=usuario_id,
        resourceid=primer_hueco.get('resource_id'),
        activityid=actividad_id,
        start_date=primer_hueco.get('date'),
        start_time=primer_hueco.get('start_time'),
        end_time=primer_hueco.get('end_time'),
        provider_session_id=primer_hueco.get('provider_session_id'),
        searchid=disponibilidad.get('searchid'),
        portal_activityid=actividad_id,  # Mismo que activityid para instancias PORTAL
        phone="670252676",
        tags="WEB_NO_ASEGURADO"
    )
    
    # Verificar resultado
    if resultado.get('success'):
        print("\n✅ Reserva creada exitosamente")
        
        # Intentar extraer el ID de la reserva
        import re
        resid_match = re.search(r'"resid":\s*"([^"]+)"', resultado.get('raw_response', ''))
        if resid_match:
            print(f"ID de la reserva: {resid_match.group(1)}")
    else:
        print(f"\n❌ Error al crear la reserva: {resultado.get('message', '')}")

if __name__ == "__main__":
    print("EJEMPLO DE FLUJO COMPLETO DE RESERVA EN TUOTEMPO")
    print("===============================================")
    ejemplo_flujo_completo()

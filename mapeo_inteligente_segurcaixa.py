"""
Mapeo Inteligente para Llamadas Segurcaixa

Este módulo contiene la lógica avanzada para mapear los datos de Pearl AI
a los campos de la API actualizar_resultado, incluyendo análisis del resumen
de la llamada para inferir el estado correcto.
"""

import re
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MapeadorInteligente:
    def __init__(self):
        """Inicializar el mapeador con patrones de reconocimiento"""
        
        # Estados de Nivel 1 válidos
        self.estados_nivel_1 = {
            'VOLVER_A_LLAMAR': 'Volver a llamar',
            'CONFIRMADO': 'CONFIRMADO', 
            'NO_INTERESADO': 'No Interesado'
        }
        
        # Estados de Nivel 2 por cada Nivel 1
        self.estados_nivel_2 = {
            'Volver a llamar': [
                'buzón',
                'no disponible cliente', 
                'Interesado. Problema técnico'
            ],
            'CONFIRMADO': [
                'Con Pack',
                'Sin Pack'
            ],
            'No Interesado': [
                'no disponiblidad cliente',
                'a corto plazo (vac. Trabajo .. )',
                'Descontento con Adeslas',
                'No da motivos',
                'Próxima baja',
                'Ya ha ido a la clínica'
            ]
        }
        
        # Patrones para detectar diferentes tipos de resultado
        self.patrones_estado = {
            'confirmado_con_pack': [
                r'contrata',
                r'acepta.*pack',
                r'quiere.*pack', 
                r'interesado.*pack',
                r'pack.*sí',
                r'con.*pack',
                r'importancia.*prevención',
                r'p[óo]liza.*incluye'
            ],
            'confirmado_sin_pack': [
                r'cita.*programada',
                r'agenda.*cita',
                r'reserva.*confirmada',
                r'fecha.*confirmada',
                r'programar.*(\d{1,2}[/-]\d{1,2})',
                r'(\d{1,2}:\d{2})',  # Hora específica
                r'sin.*pack',
                r'solo.*cita'
            ],
            'buzon': [
                r'buzón',
                r'voicemail',
                r'no.*contesta',
                r'llamada.*perdida',
                r'no.*responde',
                r'no.*coge'
            ],
            'no_disponible': [
                r'ocupado',
                r'en.*reunión',
                r'mal.*momento',
                r'no.*puede.*hablar',
                r'trabajando',
                r'llamar.*más.*tarde'
            ],
            'problema_tecnico': [
                r'error.*técnico',
                r'problema.*conexión',
                r'no.*funciona',
                r'fallo.*sistema',
                r'cortada.*llamada',
                r'mala.*conexión'
            ],
            'no_disponibilidad_cliente': [
                r'no.*necesita',
                r'no.*le.*hace.*falta',
                r'ya.*cubierto'
            ],
            'corto_plazo': [
                r'vacaciones',
                r'trabajo',
                r'viaje',
                r'mudanza',
                r'temporal'
            ],
            'descontento_adeslas': [
                r'descontento.*adeslas',
                r'problema.*adeslas',
                r'mal.*servicio',
                r'no.*gusta.*adeslas'
            ],
            'no_da_motivos': [
                r'no.*explica',
                r'no.*da.*motivo',
                r'simplemente.*no',
                r'no.*quiere.*hablar',
                r'no.*interesa',
                r'no.*le.*interesa',
                r'no.*necesita'
            ],
            'proxima_baja': [
                r'dar.*baja',
                r'cancelar.*seguro',
                r'cambiar.*compañía',
                r'dejar.*adeslas'
            ],
            'ya_ha_ido': [
                r'ya.*fue',
                r'ya.*visitó',
                r'ya.*ha.*ido',
                r'ya.*tiene.*cita',
                r'ya.*fui',
                r'acabe.*de.*ir',
                r'fui.*hace.*poco',
                r'reciente.*visita'
            ]
        }
    
    def analizar_resumen(self, resumen):
        """
        Analizar el resumen de la llamada para detectar el estado
        
        Args:
            resumen (str): Resumen de la conversación
            
        Returns:
            dict: Estado detectado y confianza
        """
        if not resumen or resumen is None:
            return {'estado': 'sin_clasificar', 'confianza': 0}
        
        # Convertir a string si no lo es ya
        resumen_str = str(resumen) if resumen is not None else ""
        if not resumen_str.strip():
            return {'estado': 'sin_clasificar', 'confianza': 0}
            
        resumen_lower = resumen_str.lower()
        resultados = {}
        
        # Buscar patrones en el resumen
        for estado, patrones in self.patrones_estado.items():
            puntuacion = 0
            matches = []
            
            for patron in patrones:
                if re.search(patron, resumen_lower):
                    puntuacion += 1
                    matches.append(patron)
            
            if puntuacion > 0:
                resultados[estado] = {
                    'puntuacion': puntuacion,
                    'matches': matches
                }
        
        # Determinar el estado más probable
        if not resultados:
            return {'estado': 'sin_clasificar', 'confianza': 0}
        
        estado_ganador = max(resultados.keys(), key=lambda k: resultados[k]['puntuacion'])
        confianza = min(resultados[estado_ganador]['puntuacion'] * 20, 100)  # Max 100%
        
        return {
            'estado': estado_ganador,
            'confianza': confianza,
            'detalles': resultados[estado_ganador]
        }
    
    def extraer_fecha_hora(self, resumen):
        """
        Extraer fechas y horas mencionadas en el resumen
        
        Args:
            resumen (str): Texto del resumen
            
        Returns:
            dict: Fechas y horas encontradas
        """
        if not resumen or resumen is None:
            return {}
        
        # Convertir a string si no lo es ya
        resumen_str = str(resumen) if resumen is not None else ""
        if not resumen_str.strip():
            return {}
        
        resultado = {}
        
        # Patrones de fecha
        patrones_fecha = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2})\s+de\s+(\w+)',             # DD de Mes
        ]
        
        # Patrones de hora
        patrones_hora = [
            r'(\d{1,2}):(\d{2})',                  # HH:MM
            r'(\d{1,2})\s*h\s*(\d{2})?',          # 14h30 o 14h
        ]
        
        for patron in patrones_fecha:
            match = re.search(patron, resumen_str)
            if match:
                resultado['fecha_raw'] = match.group(0)
                break
        
        for patron in patrones_hora:
            match = re.search(patron, resumen_str)
            if match:
                resultado['hora_raw'] = match.group(0)
                break
        
        return resultado
    
    def determinar_estado_final(self, resumen_llamada):
        """
        Determinar el estado final basado en el análisis del resumen
        
        Args:
            resumen_llamada (str): Resumen de la conversación
            
        Returns:
            dict: {'nivel_1': str, 'nivel_2': str, 'confianza': int}
        """
        if not resumen_llamada:
            return {
                'nivel_1': 'Volver a llamar',
                'nivel_2': 'no disponible cliente', 
                'confianza': 0
            }
        
        analisis = self.analizar_resumen(resumen_llamada)
        estado_detectado = analisis['estado']
        confianza = analisis.get('confianza', 0)
        
        # Mapeo de estados detectados a estados finales
        if estado_detectado in ['confirmado_con_pack']:
            return {
                'nivel_1': 'CONFIRMADO',
                'nivel_2': 'Con Pack',
                'confianza': confianza
            }
        elif estado_detectado in ['confirmado_sin_pack']:
            return {
                'nivel_1': 'CONFIRMADO', 
                'nivel_2': 'Sin Pack',
                'confianza': confianza
            }
        elif estado_detectado == 'buzon':
            return {
                'nivel_1': 'Volver a llamar',
                'nivel_2': 'buzón',
                'confianza': confianza
            }
        elif estado_detectado == 'no_disponible':
            return {
                'nivel_1': 'Volver a llamar',
                'nivel_2': 'no disponible cliente',
                'confianza': confianza
            }
        elif estado_detectado == 'problema_tecnico':
            return {
                'nivel_1': 'Volver a llamar',
                'nivel_2': 'Interesado. Problema técnico',
                'confianza': confianza
            }
        elif estado_detectado == 'no_disponibilidad_cliente':
            return {
                'nivel_1': 'No Interesado',
                'nivel_2': 'no disponiblidad cliente',
                'confianza': confianza
            }
        elif estado_detectado == 'corto_plazo':
            return {
                'nivel_1': 'No Interesado',
                'nivel_2': 'a corto plazo (vac. Trabajo .. )',
                'confianza': confianza
            }
        elif estado_detectado == 'descontento_adeslas':
            return {
                'nivel_1': 'No Interesado',
                'nivel_2': 'Descontento con Adeslas',
                'confianza': confianza
            }
        elif estado_detectado == 'no_da_motivos':
            return {
                'nivel_1': 'No Interesado',
                'nivel_2': 'No da motivos',
                'confianza': confianza
            }
        elif estado_detectado == 'proxima_baja':
            return {
                'nivel_1': 'No Interesado',
                'nivel_2': 'Próxima baja',
                'confianza': confianza
            }
        elif estado_detectado == 'ya_ha_ido':
            return {
                'nivel_1': 'No Interesado',
                'nivel_2': 'Ya ha ido a la clínica',
                'confianza': confianza
            }
        else:
            # Estado por defecto
            return {
                'nivel_1': 'Volver a llamar',
                'nivel_2': 'no disponible cliente',
                'confianza': 0
            }
    
    def mapear_a_api_payload_desde_json(self, collected_info_json):
        """
        Mapear datos directamente desde el JSON collectedInfo a payload de API
        
        Args:
            collected_info_json (dict): JSON completo de collectedInfo
            
        Returns:
            dict: Payload completo para la API
        """
        # Extraer y limpiar teléfono
        telefono = collected_info_json.get('phoneNumber', '').strip()
        if telefono.startswith('+34'):
            telefono = telefono[3:]
        elif telefono.startswith('34') and len(telefono) == 11:
            telefono = telefono[2:]
        
        if not telefono:
            logger.error("No se encontró número de teléfono válido")
            return None
        
        # Payload base
        payload = {"telefono": telefono}
        
        # Mapear campos booleanos directamente
        if collected_info_json.get('noInteresado', False):
            payload["noInteresado"] = True
            razon = collected_info_json.get('razonNoInteres', '')
            if razon:
                payload["razonNoInteres"] = razon
            else:
                payload["razonNoInteres"] = "Cliente no interesado"
            
            # Mapear código de no interés (por defecto "otros")
            payload["codigoNoInteres"] = "otros"
        
        elif collected_info_json.get('conPack', False):
            # Solo si tenemos fecha y hora válidas
            fecha = collected_info_json.get('fechaEscogida', '')
            hora = collected_info_json.get('horaEscogida', '')
            
            if fecha and hora:
                payload["conPack"] = True
                # Convertir fecha de YYYYMMDD a YYYY-MM-DD
                if len(fecha) == 8:
                    fecha_formateada = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}"
                else:
                    # Intentar normalizar otros formatos de fecha
                    try:
                        # Eliminar cualquier carácter no numérico excepto guiones y espacios
                        fecha_limpia = re.sub(r'[^0-9\-\s]', '', fecha)
                        
                        # Intentar detectar diferentes patrones
                        if re.match(r'^\d{4}\s+\d{2}[:\-]\d{2}$', fecha_limpia):  # '2025 07-31' o '2025 07:31'
                            año = fecha_limpia[:4]
                            resto = fecha_limpia[5:].replace(':', '-')
                            mes_dia = resto.split('-')
                            if len(mes_dia) == 2:
                                fecha_formateada = f"{año}-{mes_dia[0]}-{mes_dia[1]}"
                            else:
                                # Si no podemos parsear, usar formato ISO
                                fecha_formateada = datetime.now().strftime('%Y-%m-%d')
                                logger.warning(f"Formato de fecha no reconocido: {fecha}, usando fecha actual")
                        elif re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', fecha_limpia):  # 'DD/MM/YYYY' o 'DD-MM-YYYY'
                            partes = re.split(r'[/-]', fecha_limpia)
                            fecha_formateada = f"{partes[2]}-{partes[1]}-{partes[0]}"
                        elif re.match(r'^\d{4}[/-]\d{1,2}[/-]\d{1,2}$', fecha_limpia):  # 'YYYY/MM/DD' o 'YYYY-MM-DD'
                            # Ya está en formato correcto, solo asegurar que tenga guiones
                            partes = re.split(r'[/-]', fecha_limpia)
                            fecha_formateada = f"{partes[0]}-{partes[1]}-{partes[2]}"
                        else:
                            # Si no podemos parsear, usar formato ISO
                            fecha_formateada = datetime.now().strftime('%Y-%m-%d')
                            logger.warning(f"Formato de fecha no reconocido: {fecha}, usando fecha actual")
                    except Exception as e:
                        fecha_formateada = datetime.now().strftime('%Y-%m-%d')
                        logger.error(f"Error procesando fecha '{fecha}': {e}. Usando fecha actual.")
                
                # Normalizar formato de hora
                hora_limpia = hora.strip()
                if not re.match(r'^\d{1,2}:\d{2}$', hora_limpia):
                    # Si la hora no está en formato HH:MM, intentar normalizarla
                    try:
                        hora_limpia = re.sub(r'[^0-9:]', '', hora_limpia)
                        if re.match(r'^\d{1,2}\d{2}$', hora_limpia):  # '1430'
                            hora_limpia = f"{hora_limpia[:-2]}:{hora_limpia[-2:]}"
                        elif not ':' in hora_limpia:
                            hora_limpia = f"{hora_limpia}:00"
                    except:
                        hora_limpia = "12:00"  # Hora por defecto
                        logger.warning(f"Formato de hora no reconocido: {hora}, usando 12:00")
                
                payload["nuevaCita"] = f"{fecha_formateada} {hora_limpia}"
            else:
                # ConPack=True pero sin fecha/hora: verificar si es "no interesado"
                if collected_info_json.get('noInteresado', False):
                    payload["noInteresado"] = True
                    razon = collected_info_json.get('razonNoInteres', '')
                    if razon:
                        payload["razonNoInteres"] = razon
                    else:
                        payload["razonNoInteres"] = "Cliente no interesado (conPack=True pero sin fecha)"
                    payload["codigoNoInteres"] = "otros"
                    logger.info(f"ConPack=True pero sin fecha/hora y noInteresado=True -> marcado como no interesado")
                else:
                    # Sin fecha válida y sin noInteresado, tratar como volver a llamar
                    payload["volverALlamar"] = True
                    payload["razonvueltaallamar"] = "ConPack marcado pero sin fecha/hora de cita"
                    payload["codigoVolverLlamar"] = "interrupcion"
                    logger.info(f"ConPack=True pero sin fecha/hora y noInteresado=False -> volver a llamar")
        
        elif collected_info_json.get('sinPack', False):
            # Solo si tenemos fecha y hora válidas
            fecha = collected_info_json.get('fechaEscogida', '')
            hora = collected_info_json.get('horaEscogida', '')
            
            if fecha and hora:
                # Convertir fecha de YYYYMMDD a YYYY-MM-DD
                if len(fecha) == 8:
                    fecha_formateada = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}"
                else:
                    # Intentar normalizar otros formatos de fecha
                    try:
                        # Eliminar cualquier carácter no numérico excepto guiones y espacios
                        fecha_limpia = re.sub(r'[^0-9\-\s]', '', fecha)
                        
                        # Intentar detectar diferentes patrones
                        if re.match(r'^\d{4}\s+\d{2}[:\-]\d{2}$', fecha_limpia):  # '2025 07-31' o '2025 07:31'
                            año = fecha_limpia[:4]
                            resto = fecha_limpia[5:].replace(':', '-')
                            mes_dia = resto.split('-')
                            if len(mes_dia) == 2:
                                fecha_formateada = f"{año}-{mes_dia[0]}-{mes_dia[1]}"
                            else:
                                # Si no podemos parsear, usar formato ISO
                                fecha_formateada = datetime.now().strftime('%Y-%m-%d')
                                logger.warning(f"Formato de fecha no reconocido: {fecha}, usando fecha actual")
                        elif re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', fecha_limpia):  # 'DD/MM/YYYY' o 'DD-MM-YYYY'
                            partes = re.split(r'[/-]', fecha_limpia)
                            fecha_formateada = f"{partes[2]}-{partes[1]}-{partes[0]}"
                        elif re.match(r'^\d{4}[/-]\d{1,2}[/-]\d{1,2}$', fecha_limpia):  # 'YYYY/MM/DD' o 'YYYY-MM-DD'
                            # Ya está en formato correcto, solo asegurar que tenga guiones
                            partes = re.split(r'[/-]', fecha_limpia)
                            fecha_formateada = f"{partes[0]}-{partes[1]}-{partes[2]}"
                        else:
                            # Si no podemos parsear, usar formato ISO
                            fecha_formateada = datetime.now().strftime('%Y-%m-%d')
                            logger.warning(f"Formato de fecha no reconocido: {fecha}, usando fecha actual")
                    except Exception as e:
                        fecha_formateada = datetime.now().strftime('%Y-%m-%d')
                        logger.error(f"Error procesando fecha '{fecha}': {e}. Usando fecha actual.")
                
                # Normalizar formato de hora
                hora_limpia = hora.strip()
                if not re.match(r'^\d{1,2}:\d{2}$', hora_limpia):
                    # Si la hora no está en formato HH:MM, intentar normalizarla
                    try:
                        hora_limpia = re.sub(r'[^0-9:]', '', hora_limpia)
                        if re.match(r'^\d{1,2}\d{2}$', hora_limpia):  # '1430'
                            hora_limpia = f"{hora_limpia[:-2]}:{hora_limpia[-2:]}"
                        elif not ':' in hora_limpia:
                            hora_limpia = f"{hora_limpia}:00"
                    except:
                        hora_limpia = "12:00"  # Hora por defecto
                        logger.warning(f"Formato de hora no reconocido: {hora}, usando 12:00")
                
                payload["nuevaCita"] = f"{fecha_formateada} {hora_limpia}"
            else:
                # SinPack=True pero sin fecha/hora: verificar si es "no interesado"
                if collected_info_json.get('noInteresado', False):
                    payload["noInteresado"] = True
                    razon = collected_info_json.get('razonNoInteres', '')
                    if razon:
                        payload["razonNoInteres"] = razon
                    else:
                        payload["razonNoInteres"] = "Cliente no interesado (sinPack=True pero sin fecha)"
                    payload["codigoNoInteres"] = "otros"
                    logger.info(f"SinPack=True pero sin fecha/hora y noInteresado=True -> marcado como no interesado")
                else:
                    # Sin fecha válida y sin noInteresado, tratar como volver a llamar
                    payload["volverALlamar"] = True
                    payload["razonvueltaallamar"] = "SinPack marcado pero sin fecha/hora de cita"
                    payload["codigoVolverLlamar"] = "interrupcion"
                    logger.info(f"SinPack=True pero sin fecha/hora y noInteresado=False -> volver a llamar")
        
        elif collected_info_json.get('volverALlamar', False):
            payload["volverALlamar"] = True
            razon = collected_info_json.get('razonVolverALlamar', '')
            if razon:
                payload["razonvueltaallamar"] = razon
            else:
                payload["razonvueltaallamar"] = "Volver a llamar"
            
            # Por defecto interrupción, se puede ajustar según la razón
            payload["codigoVolverLlamar"] = "interrupcion"
        
        else:
            # Si no hay ningún flag específico, marcar como volver a llamar
            payload["volverALlamar"] = True
            payload["razonvueltaallamar"] = "Llamada procesada sin resultado específico"
            payload["codigoVolverLlamar"] = "interrupcion"
        
        # Agregar información del cliente
        info_cliente = []
        if collected_info_json.get('firstName'):
            info_cliente.append(f"Nombre: {collected_info_json['firstName']}")
        if collected_info_json.get('lastName'):
            info_cliente.append(f"Apellidos: {collected_info_json['lastName']}")
        if collected_info_json.get('nombreClinica'):
            info_cliente.append(f"Clínica: {collected_info_json['nombreClinica']}")
        
        if info_cliente:
            nota_info = " | ".join(info_cliente)
            if "razonvueltaallamar" in payload:
                if payload["razonvueltaallamar"]:
                    # Asegurar que es string antes de concatenar
                    razon_actual = str(payload["razonvueltaallamar"]) if not isinstance(payload["razonvueltaallamar"], str) else payload["razonvueltaallamar"]
                    payload["razonvueltaallamar"] = f"{razon_actual} [{nota_info}]"
                else:
                    payload["razonvueltaallamar"] = f"[{nota_info}]"
            elif "razonNoInteres" in payload:
                if payload["razonNoInteres"]:
                    # Asegurar que es string antes de concatenar
                    razon_actual = str(payload["razonNoInteres"]) if not isinstance(payload["razonNoInteres"], str) else payload["razonNoInteres"]
                    payload["razonNoInteres"] = f"{razon_actual} [{nota_info}]"
                else:
                    payload["razonNoInteres"] = f"[{nota_info}]"
        
        return payload
    
    def mapear_a_api_payload(self, collected_info, resumen_llamada="", duracion_segundos=0):
        """
        Mapear datos completos a payload de API con análisis inteligente
        
        Args:
            collected_info (dict): Datos del JSON collectedInfo
            resumen_llamada (str): Resumen de la conversación
            duracion_segundos (int): Duración de la llamada
            
        Returns:
            dict: Payload completo para la API
        """
        # Extraer y limpiar teléfono
        telefono = collected_info.get('phoneNumber', '').strip()
        if telefono.startswith('+34'):
            telefono = telefono[3:]
        elif telefono.startswith('34') and len(telefono) == 11:
            telefono = telefono[2:]
        
        if not telefono:
            logger.error("No se encontró número de teléfono válido")
            return None
        
        # Determinar estado final
        estado_final = self.determinar_estado_final(resumen_llamada)
        nivel_1 = estado_final['nivel_1']
        nivel_2 = estado_final['nivel_2']
        confianza = estado_final['confianza']
        
        logger.info(f"Estado detectado: {nivel_1} -> {nivel_2} (confianza: {confianza}%)")
        
        # Payload base
        payload = {"telefono": telefono}
        
        # Mapear según el estado detectado
        if nivel_1 == 'CONFIRMADO':
            if nivel_2 == 'Con Pack':
                payload["conPack"] = True
                # Intentar extraer fecha de cita
                fecha_hora = self.extraer_fecha_hora(resumen_llamada)
                if fecha_hora.get('fecha_raw') and fecha_hora.get('hora_raw'):
                    try:
                        fecha_str = fecha_hora['fecha_raw']
                        hora_str = fecha_hora['hora_raw']
                        payload["nuevaCita"] = f"{fecha_str} {hora_str}"
                    except:
                        payload["nuevaCita"] = "2025-01-01 10:00"  # Placeholder para revisión
                else:
                    payload["nuevaCita"] = "2025-01-01 10:00"  # Placeholder para revisión
            else:  # Sin Pack
                # Solo cita, sin pack
                fecha_hora = self.extraer_fecha_hora(resumen_llamada)
                if fecha_hora.get('fecha_raw') and fecha_hora.get('hora_raw'):
                    try:
                        fecha_str = fecha_hora['fecha_raw'] 
                        hora_str = fecha_hora['hora_raw']
                        payload["nuevaCita"] = f"{fecha_str} {hora_str}"
                    except:
                        payload["nuevaCita"] = "2025-01-01 10:00"  # Placeholder para revisión
                else:
                    payload["nuevaCita"] = "2025-01-01 10:00"  # Placeholder para revisión
        
        elif nivel_1 == 'Volver a llamar':
            payload["volverALlamar"] = True
            
            if nivel_2 == 'buzón':
                payload["buzon"] = True
                payload["codigoVolverLlamar"] = "buzon"
                payload["razonvueltaallamar"] = "Llamada cayó en buzón de voz"
            elif nivel_2 == 'no disponible cliente':
                payload["codigoVolverLlamar"] = "interrupcion"
                payload["razonvueltaallamar"] = "Cliente no disponible para hablar"
            elif nivel_2 == 'Interesado. Problema técnico':
                payload["errorTecnico"] = True
                payload["codigoVolverLlamar"] = "proble_tecnico"
                payload["razonvueltaallamar"] = "Problema técnico durante la llamada"
            
            # Intentar extraer hora sugerida
            if resumen_llamada and resumen_llamada is not None:
                resumen_str = str(resumen_llamada) if resumen_llamada is not None else ""
                hora_match = re.search(r'(\d{1,2}):(\d{2})', resumen_str)
                if hora_match:
                    payload["horaRellamada"] = hora_match.group(0)
        
        elif nivel_1 == 'No Interesado':
            payload["noInteresado"] = True
            payload["razonNoInteres"] = resumen_llamada[:200] if resumen_llamada else f"Cliente no interesado: {nivel_2}"
            
            # Mapear códigos específicos
            if nivel_2 == 'no disponiblidad cliente':
                payload["codigoNoInteres"] = "no disponibilidad"
            elif nivel_2 == 'a corto plazo (vac. Trabajo .. )':
                payload["codigoNoInteres"] = "no disponibilidad"
            elif nivel_2 == 'Descontento con Adeslas':
                payload["codigoNoInteres"] = "descontento"
            elif nivel_2 == 'Próxima baja':
                payload["codigoNoInteres"] = "bajaProxima"
            else:
                payload["codigoNoInteres"] = "otros"
        
        # Agregar metadatos útiles
        if duracion_segundos > 0:
            campo_nota = payload.get("razonvueltaallamar") or payload.get("razonNoInteres", "")
            if campo_nota:
                campo_nota += f" [Duración: {duracion_segundos}s]"
                if "razonvueltaallamar" in payload:
                    payload["razonvueltaallamar"] = campo_nota
                elif "razonNoInteres" in payload:
                    payload["razonNoInteres"] = campo_nota
        
        # Agregar información del cliente si está disponible
        info_cliente = []
        if collected_info.get('firstName'):
            info_cliente.append(f"Nombre: {collected_info['firstName']}")
        if collected_info.get('lastName'):
            info_cliente.append(f"Apellidos: {collected_info['lastName']}")
        if collected_info.get('nombreClinica'):
            info_cliente.append(f"Clínica: {collected_info['nombreClinica']}")
        
        if info_cliente:
            nota_info = " | ".join(info_cliente)
            if "razonvueltaallamar" in payload:
                if payload["razonvueltaallamar"]:  # Verificar que no sea None
                    payload["razonvueltaallamar"] += f" [{nota_info}]"
                else:
                    payload["razonvueltaallamar"] = f"[{nota_info}]"
            elif "razonNoInteres" in payload:
                if payload["razonNoInteres"]:  # Verificar que no sea None
                    payload["razonNoInteres"] += f" [{nota_info}]"
                else:
                    payload["razonNoInteres"] = f"[{nota_info}]"
        
        return payload
    
    def validar_payload(self, payload):
        """
        Validar que el payload cumple con los requisitos de la API
        
        Args:
            payload (dict): Payload a validar
            
        Returns:
            tuple: (es_valido: bool, errores: list)
        """
        errores = []
        
        # Validación básica
        if not payload.get('telefono'):
            errores.append("Falta el teléfono (campo obligatorio)")
        
        # Debe tener al menos un campo adicional
        campos_adicionales = [k for k in payload.keys() if k != 'telefono']
        if not campos_adicionales:
            errores.append("Debe tener al menos un campo además del teléfono")
        
        # Validaciones de formato
        telefono = payload.get('telefono', '')
        if telefono and not re.match(r'^\d{9}$', telefono):
            errores.append(f"Formato de teléfono inválido: {telefono} (debe ser 9 dígitos)")
        
        if payload.get('nuevaCita'):
            fecha_cita = payload['nuevaCita']
            if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', fecha_cita):
                errores.append(f"Formato de fecha de cita inválido: {fecha_cita} (debe ser YYYY-MM-DD HH:MM)")
        
        if payload.get('horaRellamada'):
            hora = payload['horaRellamada']
            if not re.match(r'^\d{1,2}:\d{2}$', hora):
                errores.append(f"Formato de hora inválido: {hora} (debe ser HH:MM)")
        
        return len(errores) == 0, errores


# Función auxiliar para uso directo
def mapear_llamada_segurcaixa(collected_info, resumen="", duracion=0):
    """
    Función de conveniencia para mapear una llamada individual
    
    Args:
        collected_info (dict): Datos del JSON
        resumen (str): Resumen de la llamada
        duracion (int): Duración en segundos
        
    Returns:
        dict: Payload listo para la API o None si hay errores
    """
    mapeador = MapeadorInteligente()
    payload = mapeador.mapear_a_api_payload(collected_info, resumen, duracion)
    
    if payload:
        es_valido, errores = mapeador.validar_payload(payload)
        if not es_valido:
            logger.error(f"Payload inválido: {errores}")
            return None
    
    return payload
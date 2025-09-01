#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Estadísticas de Leads - Railway Database
Analiza los resultados de contacto usando status_level_1 y status_level_2
"""

import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
from db import get_connection # Importar la función de conexión centralizada

class LeadsStatsGenerator:
    def __init__(self):
        self.connection = None
        self.stats = {}
        
    def connect_db(self):
        """Conectar a la base de datos"""
        try:
            self.connection = get_connection()
            if not self.connection:
                 raise Exception("No se pudo obtener la conexión a la base de datos desde db.py")
            print("✅ Conexión exitosa a la base de datos")
            return True
        except Exception as e:
            print(f"❌ Error conectando a la base de datos: {e}")
            return False
    
    def get_leads_data(self, fecha_desde=None, fecha_hasta=None):
        """Obtener datos de leads con filtros de fecha opcionales"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Query base
            query = """
            SELECT 
                id,
                telefono,
                nombre,
                apellidos,
                status_level_1,
                status_level_2,
                updated_at,
                cita AS fecha_cita,
                hora_cita,
                nombre_clinica AS clinica,
            call_summary AS observaciones
            FROM leads 
            WHERE 1=1
            """
            
            params = []
            
            # Añadir filtros de fecha si se proporcionan
            if fecha_desde:
                query += " AND DATE(updated_at) >= %s"
                params.append(fecha_desde)
                
            if fecha_hasta:
                query += " AND DATE(updated_at) <= %s"
                params.append(fecha_hasta)
                
            query += " ORDER BY updated_at DESC"
            
            cursor.execute(query, params)
            leads = cursor.fetchall()
            cursor.close()
            
            print(f"📊 Obtenidos {len(leads)} leads para análisis")
            return leads
            
        except Exception as e:
            print(f"❌ Error obteniendo datos: {e}")
            return []
    
    def analyze_status_combinations(self, leads):
        """Analizar combinaciones de status_level_1 y status_level_2"""
        combinations = defaultdict(int)
        status_1_counts = Counter()
        status_2_counts = Counter()
        
        for lead in leads:
            status_1 = lead.get('status_level_1') or 'Sin definir'
            status_2 = lead.get('status_level_2') or 'Sin definir'
            
            # Contar combinaciones
            combo = f"{status_1} → {status_2}"
            combinations[combo] += 1
            
            # Contar individuales
            status_1_counts[status_1] += 1
            status_2_counts[status_2] += 1
        
        return combinations, status_1_counts, status_2_counts
    
    def analyze_appointments(self, leads):
        """Analizar citas programadas"""
        with_appointment = 0
        without_appointment = 0
        appointment_by_status = defaultdict(int)
        
        for lead in leads:
            has_appointment = bool(lead.get('fecha_cita') and lead.get('hora_cita'))
            status_1 = lead.get('status_level_1') or 'Sin definir'
            
            if has_appointment:
                with_appointment += 1
                appointment_by_status[status_1] += 1
            else:
                without_appointment += 1
        
        return {
            'con_cita': with_appointment,
            'sin_cita': without_appointment,
            'por_status': dict(appointment_by_status)
        }
    
    def analyze_by_clinic(self, leads):
        """Analizar resultados por clínica"""
        clinic_stats = defaultdict(lambda: {
            'total': 0,
            'status_1': Counter(),
            'status_2': Counter(),
            'con_cita': 0
        })
        
        for lead in leads:
            clinica = lead.get('clinica') or 'Sin asignar'
            status_1 = lead.get('status_level_1') or 'Sin definir'
            status_2 = lead.get('status_level_2') or 'Sin definir'
            has_appointment = bool(lead.get('fecha_cita') and lead.get('hora_cita'))
            
            clinic_stats[clinica]['total'] += 1
            clinic_stats[clinica]['status_1'][status_1] += 1
            clinic_stats[clinica]['status_2'][status_2] += 1
            
            if has_appointment:
                clinic_stats[clinica]['con_cita'] += 1
        
        return dict(clinic_stats)
    
    def analyze_temporal_trends(self, leads):
        """Analizar tendencias temporales"""
        daily_stats = defaultdict(lambda: {
            'total': 0,
            'contactados': 0,
            'citas': 0
        })
        
        for lead in leads:
            fecha = lead.get('updated_at')
            if fecha:
                day = fecha.date().isoformat()
                status_1 = lead.get('status_level_1') or 'Sin definir'
                has_appointment = bool(lead.get('fecha_cita') and lead.get('hora_cita'))
                
                daily_stats[day]['total'] += 1
                
                # Considerar "contactado" si tiene algún status definido
                if status_1 != 'Sin definir':
                    daily_stats[day]['contactados'] += 1
                
                if has_appointment:
                    daily_stats[day]['citas'] += 1
        
        return dict(daily_stats)
    
    def generate_report(self, fecha_desde=None, fecha_hasta=None):
        """Generar informe completo de estadísticas"""
        print("🔄 Generando informe de estadísticas...")
        
        # Obtener datos
        leads = self.get_leads_data(fecha_desde, fecha_hasta)
        if not leads:
            print("❌ No se encontraron leads para analizar")
            return
        
        # Realizar análisis
        combinations, status_1_counts, status_2_counts = self.analyze_status_combinations(leads)
        appointments = self.analyze_appointments(leads)
        clinic_stats = self.analyze_by_clinic(leads)
        temporal_trends = self.analyze_temporal_trends(leads)
        
        # Generar informe
        report = {
            'metadata': {
                'fecha_generacion': datetime.now().isoformat(),
                'total_leads': len(leads),
                'periodo': {
                    'desde': fecha_desde.isoformat() if fecha_desde else 'Todos los registros',
                    'hasta': fecha_hasta.isoformat() if fecha_hasta else 'Hasta la fecha'
                }
            },
            'resumen_general': {
                'total_leads': len(leads),
                'leads_contactados': sum(1 for lead in leads if lead.get('status_level_1')),
                'leads_con_cita': appointments['con_cita'],
                'tasa_contacto': round((sum(1 for lead in leads if lead.get('status_level_1')) / len(leads)) * 100, 2),
                'tasa_conversion_cita': round((appointments['con_cita'] / len(leads)) * 100, 2)
            },
            'status_level_1': dict(status_1_counts),
            'status_level_2': dict(status_2_counts),
            'combinaciones_status': dict(combinations),
            'analisis_citas': appointments,
            'estadisticas_por_clinica': clinic_stats,
            'tendencias_temporales': temporal_trends
        }
        
        return report
    
    def print_readable_report(self, report):
        """Imprimir informe en formato legible"""
        print("\n" + "="*80)
        print("📊 INFORME DE ESTADÍSTICAS DE LEADS")
        print("="*80)
        
        # Metadata
        meta = report['metadata']
        print(f"\n📅 Fecha de generación: {meta['fecha_generacion']}")
        print(f"📊 Total de leads analizados: {meta['total_leads']:,}")
        print(f"📆 Período: {meta['periodo']['desde']} → {meta['periodo']['hasta']}")
        
        # Resumen general
        resumen = report['resumen_general']
        print(f"\n🎯 RESUMEN GENERAL")
        print("-" * 40)
        print(f"Total leads: {resumen['total_leads']:,}")
        print(f"Leads contactados: {resumen['leads_contactados']:,}")
        print(f"Leads con cita: {resumen['leads_con_cita']:,}")
        print(f"Tasa de contacto: {resumen['tasa_contacto']}%")
        print(f"Tasa de conversión a cita: {resumen['tasa_conversion_cita']}%")
        
        # Status Level 1
        print(f"\n📞 RESULTADOS DE CONTACTO (Status Level 1)")
        print("-" * 50)
        status_1 = report['status_level_1']
        total_status_1 = sum(status_1.values())
        for status, count in sorted(status_1.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_status_1) * 100 if total_status_1 > 0 else 0
            print(f"{status:<25} {count:>6,} ({percentage:>5.1f}%)")
        
        # Status Level 2
        print(f"\n🎯 RESULTADOS DETALLADOS (Status Level 2)")
        print("-" * 50)
        status_2 = report['status_level_2']
        total_status_2 = sum(status_2.values())
        for status, count in sorted(status_2.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_status_2) * 100 if total_status_2 > 0 else 0
            print(f"{status:<25} {count:>6,} ({percentage:>5.1f}%)")
        
        # Top combinaciones
        print(f"\n🔗 TOP 10 COMBINACIONES DE STATUS")
        print("-" * 60)
        combinations = report['combinaciones_status']
        top_combinations = sorted(combinations.items(), key=lambda x: x[1], reverse=True)[:10]
        for combo, count in top_combinations:
            percentage = (count / len(report['metadata']['total_leads'])) * 100
            print(f"{combo:<40} {count:>6,} ({percentage:>5.1f}%)")
        
        # Análisis de citas
        citas = report['analisis_citas']
        print(f"\n📅 ANÁLISIS DE CITAS")
        print("-" * 30)
        print(f"Con cita programada: {citas['con_cita']:,}")
        print(f"Sin cita programada: {citas['sin_cita']:,}")
        print(f"\nCitas por Status Level 1:")
        for status, count in sorted(citas['por_status'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {status:<20} {count:>6,}")
        
        # Top clínicas
        print(f"\n🏥 TOP 10 CLÍNICAS POR VOLUMEN")
        print("-" * 50)
        clinics = report['estadisticas_por_clinica']
        top_clinics = sorted(clinics.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
        for clinica, stats in top_clinics:
            tasa_cita = (stats['con_cita'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"{clinica:<30} {stats['total']:>6,} leads ({tasa_cita:>5.1f}% con cita)")
    
    def save_report_to_file(self, report, filename=None):
        """Guardar informe en archivo JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"estadisticas_leads_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            print(f"💾 Informe guardado en: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error guardando informe: {e}")
            return None
    
    def close_connection(self):
        """Cerrar conexión a la base de datos"""
        if self.connection:
            self.connection.close()

def main():
    """Función principal"""
    print("🚀 Iniciando generador de estadísticas de leads...")
    
    # Crear generador
    generator = LeadsStatsGenerator()
    
    # Conectar a la base de datos
    if not generator.connect_db():
        return
    
    try:
        # Opciones de filtro por fecha
        print("\n📅 Opciones de filtro por fecha:")
        print("1. Todos los registros")
        print("2. Últimos 7 días")
        print("3. Últimos 30 días")
        print("4. Rango personalizado")
        
        opcion = input("\nSelecciona una opción (1-4): ").strip()
        
        fecha_desde = None
        fecha_hasta = None
        
        if opcion == "2":
            fecha_desde = datetime.now().date() - timedelta(days=7)
        elif opcion == "3":
            fecha_desde = datetime.now().date() - timedelta(days=30)
        elif opcion == "4":
            try:
                fecha_desde_str = input("Fecha desde (YYYY-MM-DD): ").strip()
                fecha_hasta_str = input("Fecha hasta (YYYY-MM-DD): ").strip()
                
                if fecha_desde_str:
                    fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
                if fecha_hasta_str:
                    fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date()
            except ValueError:
                print("❌ Formato de fecha inválido. Usando todos los registros.")
        
        # Generar informe
        report = generator.generate_report(fecha_desde, fecha_hasta)
        
        if report:
            # Mostrar informe
            generator.print_readable_report(report)
            
            # Preguntar si guardar
            save = input("\n💾 ¿Guardar informe en archivo JSON? (s/n): ").strip().lower()
            if save in ['s', 'si', 'sí', 'y', 'yes']:
                generator.save_report_to_file(report)
            
            print("\n✅ Informe generado exitosamente")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
    finally:
        generator.close_connection()

if __name__ == "__main__":
    main()

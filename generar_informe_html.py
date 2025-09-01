#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Informe HTML de Estadísticas de Leads
Crea un informe visual y legible en formato HTML
"""

import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from db import get_connection # Importar la función de conexión centralizada

def get_leads_data():
    """Obtener datos de leads"""
    connection = None  # Inicializar la variable
    try:
        connection = get_connection()
        if not connection:
            raise Exception("No se pudo obtener la conexión a la base de datos desde db.py")

        cursor = connection.cursor(dictionary=True)
        
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
        ORDER BY updated_at DESC
        """
        
        cursor.execute(query)
        leads = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return leads
        
    except Exception as e:
        print(f"❌ Error obteniendo datos: {e}")
        return []
    finally:
        if connection and connection.is_connected():
            connection.close()

def generate_html_report():
    """Generar informe HTML"""
    leads = get_leads_data()
    if not leads:
        return None
    
    # Análisis de datos
    total_leads = len(leads)
    leads_contactados = sum(1 for lead in leads if lead.get('status_level_1'))
    leads_con_cita = sum(1 for lead in leads if lead.get('fecha_cita') and lead.get('hora_cita'))
    
    # Contadores
    status_1_counts = Counter(lead.get('status_level_1') or 'Sin definir' for lead in leads)
    status_2_counts = Counter(lead.get('status_level_2') or 'Sin definir' for lead in leads)
    clinic_counts = Counter(lead.get('clinica') or 'Sin asignar' for lead in leads)
    
    # Combinaciones de status
    combinations = Counter()
    for lead in leads:
        status_1 = lead.get('status_level_1') or 'Sin definir'
        status_2 = lead.get('status_level_2') or 'Sin definir'
        combinations[f"{status_1} → {status_2}"] += 1
    
    # Generar HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Estadísticas de Leads - Tuotempo</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-top: 30px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 1.1em;
                opacity: 0.9;
            }}
            .table-container {{
                overflow-x: auto;
                margin: 20px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #3498db;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            tr:hover {{
                background-color: #e8f4f8;
            }}
            .progress-bar {{
                background: #ecf0f1;
                border-radius: 10px;
                overflow: hidden;
                height: 20px;
                margin: 5px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #3498db, #2980b9);
                transition: width 0.3s ease;
            }}
            .percentage {{
                font-weight: bold;
                color: #2c3e50;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #7f8c8d;
            }}
            .highlight {{
                background: linear-gradient(120deg, #a8edea 0%, #fed6e3 100%);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Estadísticas de Leads - Tuotempo</h1>
            
            <div class="highlight">
                <strong>📅 Fecha de generación:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}<br>
                <strong>📊 Total de leads analizados:</strong> {total_leads:,}
            </div>
            
            <h2>🎯 Resumen General</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_leads:,}</div>
                    <div class="stat-label">Total Leads</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{leads_contactados:,}</div>
                    <div class="stat-label">Leads Contactados</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{leads_con_cita:,}</div>
                    <div class="stat-label">Leads con Cita</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{(leads_contactados/total_leads*100):.1f}%</div>
                    <div class="stat-label">Tasa de Contacto</div>
                </div>
            </div>
            
            <h2>📞 Resultados de Contacto (Status Level 1)</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Estado</th>
                            <th>Cantidad</th>
                            <th>Porcentaje</th>
                            <th>Progreso</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Tabla Status Level 1
    for status, count in status_1_counts.most_common():
        percentage = (count / total_leads) * 100
        html_content += f"""
                        <tr>
                            <td><strong>{status}</strong></td>
                            <td>{count:,}</td>
                            <td class="percentage">{percentage:.1f}%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {percentage}%"></div>
                                </div>
                            </td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <h2>🎯 Resultados Detallados (Status Level 2)</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Estado Detallado</th>
                            <th>Cantidad</th>
                            <th>Porcentaje</th>
                            <th>Progreso</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Tabla Status Level 2
    for status, count in status_2_counts.most_common():
        percentage = (count / total_leads) * 100
        html_content += f"""
                        <tr>
                            <td><strong>{status}</strong></td>
                            <td>{count:,}</td>
                            <td class="percentage">{percentage:.1f}%</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {percentage}%"></div>
                                </div>
                            </td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <h2>🔗 Top 10 Combinaciones de Status</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Combinación</th>
                            <th>Cantidad</th>
                            <th>Porcentaje</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Top combinaciones
    for combo, count in combinations.most_common(10):
        percentage = (count / total_leads) * 100
        html_content += f"""
                        <tr>
                            <td><strong>{combo}</strong></td>
                            <td>{count:,}</td>
                            <td class="percentage">{percentage:.1f}%</td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <h2>🏥 Top 10 Clínicas por Volumen</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Clínica</th>
                            <th>Total Leads</th>
                            <th>Porcentaje del Total</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Top clínicas
    for clinica, count in clinic_counts.most_common(10):
        percentage = (count / total_leads) * 100
        html_content += f"""
                        <tr>
                            <td><strong>{clinica}</strong></td>
                            <td>{count:,}</td>
                            <td class="percentage">{percentage:.1f}%</td>
                        </tr>
        """
    
    html_content += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>📊 Informe generado automáticamente el {datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")}</p>
                <p>🚀 Sistema Tuotempo - Gestión de Leads</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def main():
    """Función principal"""
    print("🚀 Generando informe HTML de estadísticas...")
    
    try:
        html_content = generate_html_report()
        
        if html_content:
            # Guardar archivo HTML
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"informe_leads_{timestamp}.html"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Informe HTML generado exitosamente: {filename}")
            print(f"🌐 Abre el archivo en tu navegador para ver el informe completo")
            
            # Mostrar ruta completa
            full_path = os.path.abspath(filename)
            print(f"📁 Ruta completa: {full_path}")
            
        else:
            print("❌ No se pudo generar el informe")
            
    except Exception as e:
        print(f"❌ Error generando informe: {e}")

if __name__ == "__main__":
    main()

"""
Script de preparación para despliegue en Railway.
Verifica que todo esté listo y crea un reporte completo.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_pre_deployment_check():
    """Ejecuta todas las verificaciones antes del despliegue."""
    
    print("🚀 PREPARACIÓN PARA DESPLIEGUE EN RAILWAY")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_checks = []
    
    # 1. Verificar estructura de archivos
    print("\n📁 VERIFICANDO ESTRUCTURA DE ARCHIVOS...")
    file_structure = {
        "Backend Core": [
            "pearl_caller.py",
            "call_manager.py", 
            "api_pearl_calls.py",
            "db_migration_add_call_fields.py"
        ],
        "Frontend": [
            "templates/calls_manager.html",
            "static/css/calls_manager.css",
            "static/js/calls_manager.js"
        ],
        "Configuración": [
            "blueprints.py",
            "app_dashboard.py",
            "requirements.txt",
            ".env.example"
        ],
        "Documentación": [
            "CALLS_SYSTEM_README.md",
            "RAILWAY_DEPLOYMENT_GUIDE.md"
        ]
    }
    
    files_status = {}
    for category, files in file_structure.items():
        print(f"\n🔍 {category}:")
        category_ok = True
        for file_path in files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file_path} ({size:,} bytes)")
            else:
                print(f"  ❌ {file_path} - NO ENCONTRADO")
                category_ok = False
        files_status[category] = category_ok
    
    all_checks.append(("Estructura de Archivos", all(files_status.values())))
    
    # 2. Verificar Git Status
    print("\n🔄 VERIFICANDO ESTADO DE GIT...")
    try:
        # Verificar si hay cambios sin commit
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            if result.stdout.strip():
                print("⚠️  Hay cambios sin commit:")
                for line in result.stdout.strip().split('\n'):
                    print(f"    {line}")
                git_ok = False
            else:
                print("✅ Todos los cambios están commitados")
                git_ok = True
        else:
            print("❌ Error verificando git status")
            git_ok = False
            
    except FileNotFoundError:
        print("⚠️  Git no encontrado - verifica manualmente")
        git_ok = True  # No bloquear si git no está disponible
    
    all_checks.append(("Git Status", git_ok))
    
    # 3. Verificar Variables de Entorno
    print("\n🔑 VERIFICANDO VARIABLES DE ENTORNO...")
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = {
        "Base de Datos": ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE'],
        "Pearl AI": ['PEARL_ACCOUNT_ID', 'PEARL_SECRET_KEY'],
        "Flask": ['SECRET_KEY']
    }
    
    env_status = {}
    for category, vars_list in env_vars.items():
        print(f"\n🔍 {category}:")
        category_ok = True
        for var in vars_list:
            value = os.getenv(var)
            if value:
                if 'SECRET' in var or 'PASSWORD' in var:
                    print(f"  ✅ {var}: {'*' * min(len(value), 20)}")
                else:
                    print(f"  ✅ {var}: {value}")
            else:
                print(f"  ❌ {var}: NO CONFIGURADO")
                category_ok = False
        env_status[category] = category_ok
    
    all_checks.append(("Variables de Entorno", all(env_status.values())))
    
    # 4. Verificar Importaciones Críticas
    print("\n📦 VERIFICANDO IMPORTACIONES...")
    critical_imports = [
        ('flask', 'Flask'),
        ('mysql.connector', 'Error'), 
        ('requests', 'get'),
        ('pearl_caller', 'get_pearl_client'),
        ('call_manager', 'get_call_manager'),
        ('api_pearl_calls', 'register_calls_api')
    ]
    
    imports_ok = True
    for module, item in critical_imports:
        try:
            mod = __import__(module, fromlist=[item])
            getattr(mod, item)
            print(f"  ✅ {module}.{item}")
        except Exception as e:
            print(f"  ❌ {module}.{item}: {e}")
            imports_ok = False
    
    all_checks.append(("Importaciones", imports_ok))
    
    # 5. Generar Reporte de Pre-Despliegue
    print("\n" + "=" * 60)
    print("📋 REPORTE DE PRE-DESPLIEGUE")
    print("=" * 60)
    
    overall_status = True
    for check_name, status in all_checks:
        icon = "✅" if status else "❌"
        print(f"{icon} {check_name}")
        if not status:
            overall_status = False
    
    print("\n" + "=" * 60)
    
    if overall_status:
        print("🎉 ¡LISTO PARA DESPLIEGUE EN RAILWAY!")
        print("\n📋 Próximos pasos:")
        print("1. 🔑 Configurar variables de entorno en Railway")
        print("2. 📊 Ejecutar migración: python railway_migration.py")
        print("3. 🚀 Git push para desplegar")
        print("4. ✅ Verificar endpoints en producción")
        print("\n📖 Ver guía completa: RAILWAY_DEPLOYMENT_GUIDE.md")
    else:
        print("⚠️  REQUIERE ATENCIÓN ANTES DEL DESPLIEGUE")
        print("\n🔧 Corrige los problemas indicados arriba")
        print("📖 Consulta la documentación para más detalles")
    
    # 6. Crear archivo de reporte
    report_content = f"""# REPORTE PRE-DESPLIEGUE
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Estado: {'LISTO' if overall_status else 'REQUIERE ATENCIÓN'}

## Verificaciones:
"""
    
    for check_name, status in all_checks:
        report_content += f"- {check_name}: {'✅ OK' if status else '❌ FALLA'}\n"
    
    with open('pre_deployment_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📝 Reporte guardado en: pre_deployment_report.txt")
    
    return overall_status

if __name__ == "__main__":
    success = run_pre_deployment_check()
    sys.exit(0 if success else 1)

"""
Script de verificación para Railway - Comprueba que todo esté configurado correctamente.
"""

import os
import sys
from dotenv import load_dotenv

def check_railway_environment():
    """Verifica que el entorno de Railway esté configurado correctamente."""
    
    print("🔍 VERIFICACIÓN DE ENTORNO RAILWAY")
    print("=" * 50)
    
    # Cargar variables de entorno
    load_dotenv()
    
    checks = []
    
    # 1. Verificar Base de Datos
    print("\n📊 VERIFICANDO BASE DE DATOS...")
    db_vars = {
        'MYSQL_HOST': os.getenv('MYSQL_HOST'),
        'MYSQL_USER': os.getenv('MYSQL_USER'), 
        'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'MYSQL_DATABASE': os.getenv('MYSQL_DATABASE'),
        'MYSQL_PORT': os.getenv('MYSQL_PORT', '3306')
    }
    
    db_ok = True
    for var, value in db_vars.items():
        if value:
            print(f"✅ {var}: {'*' * len(str(value))}")
        else:
            print(f"❌ {var}: NO CONFIGURADO")
            db_ok = False
    
    checks.append(("Base de Datos", db_ok))
    
    # 2. Verificar Pearl AI
    print("\n📞 VERIFICANDO PEARL AI...")
    pearl_vars = {
        'PEARL_ACCOUNT_ID': os.getenv('PEARL_ACCOUNT_ID'),
        'PEARL_SECRET_KEY': os.getenv('PEARL_SECRET_KEY'),
        'PEARL_API_URL': os.getenv('PEARL_API_URL', 'https://api.nlpearl.ai/v1'),
        'PEARL_OUTBOUND_ID': os.getenv('PEARL_OUTBOUND_ID')
    }
    
    pearl_ok = True
    for var, value in pearl_vars.items():
        if value:
            if 'SECRET' in var or 'ACCOUNT' in var:
                print(f"✅ {var}: {'*' * min(len(str(value)), 20)}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NO CONFIGURADO")
            if var != 'PEARL_OUTBOUND_ID':  # OUTBOUND_ID es opcional
                pearl_ok = False
    
    checks.append(("Pearl AI", pearl_ok))
    
    # 3. Verificar Flask
    print("\n🌐 VERIFICANDO FLASK...")
    flask_vars = {
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'DEBUG': os.getenv('DEBUG', 'False'),
        'PORT': os.getenv('PORT', '5000')
    }
    
    flask_ok = True
    for var, value in flask_vars.items():
        if value:
            if 'SECRET' in var:
                print(f"✅ {var}: {'*' * min(len(str(value)), 20)}")
            else:
                print(f"✅ {var}: {value}")
        else:
            if var == 'SECRET_KEY':
                print(f"⚠️  {var}: NO CONFIGURADO (requerido para producción)")
                flask_ok = False
            else:
                print(f"ℹ️  {var}: Usando valor por defecto")
    
    checks.append(("Flask", flask_ok))
    
    # 4. Verificar Archivos del Sistema de Llamadas
    print("\n📁 VERIFICANDO ARCHIVOS DEL SISTEMA...")
    required_files = [
        'pearl_caller.py',
        'call_manager.py', 
        'api_pearl_calls.py',
        'templates/calls_manager.html',
        'static/css/calls_manager.css',
        'static/calls_manager.js'
    ]
    
    files_ok = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}: NO ENCONTRADO")
            files_ok = False
    
    checks.append(("Archivos del Sistema", files_ok))
    
    # 5. Probar Importaciones
    print("\n📦 VERIFICANDO IMPORTACIONES...")
    imports_ok = True
    test_imports = [
        ('pearl_caller', 'get_pearl_client'),
        ('call_manager', 'get_call_manager'), 
        ('api_pearl_calls', 'register_calls_api'),
        ('blueprints', 'register_apis')
    ]
    
    for module, function in test_imports:
        try:
            mod = __import__(module, fromlist=[function])
            getattr(mod, function)
            print(f"✅ {module}.{function}")
        except Exception as e:
            print(f"❌ {module}.{function}: {e}")
            imports_ok = False
    
    checks.append(("Importaciones", imports_ok))
    
    # 6. Resumen Final
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE VERIFICACIÓN")
    print("=" * 50)
    
    all_ok = True
    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")
        if not status:
            all_ok = False
    
    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 ¡ENTORNO RAILWAY LISTO PARA DESPLIEGUE!")
        print("✅ Todos los componentes están configurados correctamente")
    else:
        print("⚠️  ENTORNO RAILWAY REQUIERE CONFIGURACIÓN")
        print("❌ Algunos componentes necesitan atención")
    
    return all_ok

if __name__ == "__main__":
    success = check_railway_environment()
    sys.exit(0 if success else 1)

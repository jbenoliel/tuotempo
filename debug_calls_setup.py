"""
Script para verificar la configuración y depurar problemas con WebSocket y APIs.
"""

from flask import Flask
import logging
import os

# Configurar logging para depuración
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_calls_manager_setup():
    """Verifica que el setup del calls manager esté correcto."""
    print("🔍 === VERIFICANDO SETUP DE CALLS MANAGER ===")
    
    try:
        # Verificar imports críticos
        from api_pearl_calls import api_pearl_calls
        print("✅ api_pearl_calls importado correctamente")
        
        from call_manager import get_call_manager
        print("✅ call_manager importado correctamente")
        
        from pearl_caller import get_pearl_client
        print("✅ pearl_caller importado correctamente")
        
        # Verificar que el blueprint tenga las rutas esperadas
        print(f"📍 Blueprint URL prefix: {api_pearl_calls.url_prefix}")
        print("📍 Rutas registradas en el blueprint:")
        
        for rule in api_pearl_calls.url_map.iter_rules():
            print(f"   {rule.methods} {rule.rule}")
        
        # Verificar variables de entorno críticas
        print("\n🔧 Variables de entorno:")
        critical_env_vars = [
            'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_DATABASE',
            'PEARL_API_KEY', 'PEARL_BASE_URL'
        ]
        
        for var in critical_env_vars:
            value = os.getenv(var)
            if value:
                # No mostrar valores sensibles completos
                if 'KEY' in var or 'PASSWORD' in var:
                    print(f"   {var}: {'*' * min(len(value), 8)}...")
                else:
                    print(f"   {var}: {value}")
            else:
                print(f"   {var}: ❌ No configurada")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_test_app():
    """Crea una app Flask de prueba para verificar rutas."""
    print("\n🧪 === CREANDO APP DE PRUEBA ===")
    
    try:
        from app_dashboard import create_app
        app = create_app()
        
        print("✅ App creada correctamente")
        print(f"📍 Rutas registradas en la app:")
        
        for rule in app.url_map.iter_rules():
            if '/api/calls' in rule.rule:
                print(f"   {list(rule.methods)} {rule.rule} -> {rule.endpoint}")
        
        return app
        
    except Exception as e:
        print(f"❌ Error creando app: {e}")
        return None

def test_database_connection():
    """Prueba la conexión a la base de datos."""
    print("\n🗄️ === VERIFICANDO CONEXIÓN A BD ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Probar consulta simple
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        
        print(f"✅ Conexión a BD exitosa")
        print(f"📊 Total de leads en BD: {count}")
        
        # Verificar estructura de tabla leads
        cursor.execute("DESCRIBE leads")
        columns = cursor.fetchall()
        
        print("📋 Columnas en tabla 'leads':")
        for col in columns:
            print(f"   {col[0]} - {col[1]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error de BD: {e}")
        return False

def test_pearl_connection():
    """Prueba la conexión con Pearl AI."""
    print("\n🤖 === VERIFICANDO CONEXIÓN PEARL AI ===")
    
    try:
        from pearl_caller import get_pearl_client
        
        client = get_pearl_client()
        print(f"✅ Cliente Pearl creado")
        
        # Probar conexión
        if client.test_connection():
            print("✅ Conexión con Pearl AI exitosa")
            
            # Obtener información adicional si es posible
            try:
                outbound_id = client.get_default_outbound_id()
                print(f"📞 Default Outbound ID: {outbound_id}")
            except:
                print("⚠️ No se pudo obtener outbound ID")
            
            return True
        else:
            print("❌ Conexión con Pearl AI fallida")
            return False
            
    except Exception as e:
        print(f"❌ Error Pearl: {e}")
        return False

def main():
    """Función principal de depuración."""
    print("🔧 === HERRAMIENTA DE DEPURACIÓN CALLS MANAGER ===")
    print("Esta herramienta verifica la configuración del sistema de llamadas\n")
    
    checks = [
        ("Setup general", check_calls_manager_setup),
        ("Conexión BD", test_database_connection),
        ("Conexión Pearl AI", test_pearl_connection),
        ("App Flask", lambda: create_test_app() is not None)
    ]
    
    results = []
    
    for name, check_func in checks:
        print(f"\n{'='*20} {name.upper()} {'='*20}")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            results.append((name, False))
    
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE VERIFICACIONES:")
    
    for name, result in results:
        status = "✅ OK" if result else "❌ ERROR"
        print(f"   {name}: {status}")
    
    if all(result for _, result in results):
        print("\n🎉 ¡Todo está configurado correctamente!")
        print("Si sigues teniendo problemas, revisa los logs del servidor.")
    else:
        print("\n⚠️ Hay problemas de configuración que deben solucionarse.")
    
    print(f"\n💡 PRÓXIMOS PASOS:")
    print("1. Ejecuta este script: python test_calls_endpoints.py")
    print("2. Inicia tu servidor Flask")
    print("3. Abre la página calls-manager y revisa la consola del navegador")
    print("4. Si sigues viendo errores 404, verifica que el blueprint esté registrado")

if __name__ == "__main__":
    main()

"""
Script para ejecutar la migración en Railway (producción).
Ejecuta la migración contra la base de datos remota de Railway.
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def run_railway_migration():
    """Ejecuta la migración en la base de datos de Railway."""
    
    print("🚄 Ejecutando migración en Railway...")
    print("🔧 Verificando conexión a base de datos de Railway...")
    
    # Verificar que las variables de entorno estén configuradas
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}")
        print("   Configura las variables en Railway o en tu .env")
        return False
    
    # Mostrar información de conexión (sin credenciales)
    print(f"🔗 Conectando a: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}")
    print(f"📊 Base de datos: {os.getenv('MYSQL_DATABASE')}")
    print(f"👤 Usuario: {os.getenv('MYSQL_USER')}")
    
    try:
        # Importar y ejecutar la migración
        from db_migration_add_call_fields import run_migration
        
        print("\n🚀 Iniciando migración en Railway...")
        success = run_migration()
        
        if success:
            print("\n✅ ¡Migración en Railway completada exitosamente!")
            print("🎯 Los nuevos campos están disponibles en producción")
            return True
        else:
            print("\n❌ Error en la migración de Railway")
            return False
            
    except Exception as e:
        print(f"\n❌ Error ejecutando migración: {e}")
        return False

if __name__ == "__main__":
    success = run_railway_migration()
    sys.exit(0 if success else 1)

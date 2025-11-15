"""
Script de migración para actualizar la base de datos existente.
Ejecutar solo una vez para agregar las nuevas columnas y tablas.
"""
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Obtener el tipo de base de datos
    engine = db.engine
    
    print("🔄 Iniciando migración de base de datos...")
    
    try:
        # Crear todas las tablas basadas en los modelos de SQLAlchemy
        print("➡️ Creando todas las tablas...")
        db.create_all()
        print("   ✅ Tablas creadas exitosamente.")
        
        print("\n✅ Migración completada.")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        raise

print("\n✨ Puedes reiniciar el servidor ahora")

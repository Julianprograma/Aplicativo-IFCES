"""
Script de migración para agregar las tablas de FASE 2 y FASE 3
Ejecutar: python migrate_fase2_fase3.py
"""
from app import create_app, db
from app.models import Notificacion, Certificado, ExamenResultado

def migrate():
    app = create_app()
    with app.app_context():
        print("Iniciando migración FASE 2 y FASE 3...")
        
        try:
            # Crear nuevas tablas
            db.create_all()
            print("✅ Tablas creadas exitosamente")
            
            # Verificar que las columnas nuevas existan en ExamenResultado
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('examenes_resultados')]
            
            print(f"\nColumnas en examenes_resultados: {columns}")
            
            # Verificar que las nuevas tablas existan
            tables = inspector.get_table_names()
            print(f"\nTablas en la base de datos: {tables}")
            
            if 'notificaciones' in tables:
                print("✅ Tabla 'notificaciones' creada")
            else:
                print("❌ Tabla 'notificaciones' no encontrada")
            
            if 'certificados' in tables:
                print("✅ Tabla 'certificados' creada")
            else:
                print("❌ Tabla 'certificados' no encontrada")
            
            print("\n✅ Migración completada exitosamente!")
            
        except Exception as e:
            print(f"❌ Error durante la migración: {e}")
            db.session.rollback()

if __name__ == "__main__":
    migrate()

"""
Script para agregar las columnas nuevas a la tabla examenes_resultados
"""
from app import create_app, db

def add_columns():
    app = create_app()
    with app.app_context():
        print("Agregando columnas nuevas a examenes_resultados...")
        
        try:
            # Agregar columnas una por una
            columns_to_add = [
                "ALTER TABLE examenes_resultados ADD COLUMN es_modo_practica BOOLEAN DEFAULT 0",
                "ALTER TABLE examenes_resultados ADD COLUMN solicitud_revision BOOLEAN DEFAULT 0",
                "ALTER TABLE examenes_resultados ADD COLUMN revision_completada BOOLEAN DEFAULT 0",
                "ALTER TABLE examenes_resultados ADD COLUMN fecha_solicitud_revision DATETIME"
            ]
            
            for sql in columns_to_add:
                try:
                    db.session.execute(db.text(sql))
                    db.session.commit()
                    print(f"✅ Columna agregada: {sql.split('ADD COLUMN')[1].split()[0]}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"⚠️  Columna ya existe: {sql.split('ADD COLUMN')[1].split()[0]}")
                    else:
                        print(f"❌ Error: {e}")
                    db.session.rollback()
            
            print("\n✅ Migración completada!")
            
            # Verificar columnas
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('examenes_resultados')]
            print(f"\nColumnas actuales en examenes_resultados:")
            for col in columns:
                print(f"  - {col}")
                
        except Exception as e:
            print(f"❌ Error general: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_columns()

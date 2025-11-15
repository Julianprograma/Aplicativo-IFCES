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
        # Agregar columna is_active a users si no existe
        print("➡️ Agregando columna 'is_active' a tabla 'users'...")
        with engine.connect() as conn:
            # Para SQLite
            if 'sqlite' in str(engine.url):
                # Verificar si la columna ya existe
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result]
                
                if 'is_active' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
                    conn.commit()
                    print("   ✅ Columna 'is_active' agregada")
                else:
                    print("   ℹ️ Columna 'is_active' ya existe")
            
            # Para MySQL
            elif 'mysql' in str(engine.url):
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1 NOT NULL"))
                    conn.commit()
                    print("   ✅ Columna 'is_active' agregada")
                except Exception as e:
                    if 'Duplicate column name' in str(e):
                        print("   ℹ️ Columna 'is_active' ya existe")
                    else:
                        raise
        
        # Crear tablas nuevas (examenes y estudiante_examen)
        print("➡️ Creando nuevas tablas...")
        db.create_all()
        print("   ✅ Tablas creadas/verificadas")
        
        print("\n✅ Migración completada exitosamente")
        print("\n📋 Estructura actualizada:")
        print("   - users: id, username, email, password_hash, role, is_active, created_at")
        print("   - examenes: id, titulo, descripcion, fecha_creacion, profesor_id")
        print("   - estudiante_examen: estudiante_id, examen_id, asignado_en")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        print("   Si el error persiste, considera eliminar instance/app.db y reiniciar")
        raise

print("\n✨ Puedes reiniciar el servidor ahora")

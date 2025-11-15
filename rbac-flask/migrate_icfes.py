"""
Migración para agregar características estilo ICFES:
- Tabla categorias
- categoria_id en examenes
- nivel_dificultad, tiempo_estimado, explicacion, imagen_url en preguntas
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db


def migrate():
    app = create_app()
    
    with app.app_context():
        engine_name = db.engine.name
        print(f"🔍 Base de datos: {engine_name}")
        
        # Crear tabla categorias
        print("\n📦 Creando tabla categorias...")
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(100) NOT NULL UNIQUE,
                descripcion TEXT,
                color VARCHAR(7) DEFAULT '#00695c',
                icono VARCHAR(50),
                activo BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
        print("✅ Tabla categorias creada")
        
        # Agregar categorías por defecto
        print("\n📝 Agregando categorías por defecto...")
        categorias_default = [
            ("Matemáticas", "Razonamiento matemático y cuantitativo", "#1976d2", "🔢"),
            ("Lectura Crítica", "Comprensión lectora y análisis textual", "#388e3c", "📖"),
            ("Ciencias Naturales", "Biología, Física y Química", "#7b1fa2", "🔬"),
            ("Ciencias Sociales", "Historia, Geografía y Política", "#f57c00", "🌍"),
            ("Inglés", "Comprensión y uso del idioma inglés", "#0097a7", "🌐"),
            ("General", "Conocimientos generales y misceláneos", "#00695c", "📚")
        ]
        
        for nombre, desc, color, icono in categorias_default:
            db.session.execute(db.text("""
                INSERT OR IGNORE INTO categorias (nombre, descripcion, color, icono)
                VALUES (:nombre, :desc, :color, :icono)
            """), {"nombre": nombre, "desc": desc, "color": color, "icono": icono})
        db.session.commit()
        print("✅ Categorías por defecto agregadas")
        
        # Agregar categoria_id a examenes
        print("\n➕ Agregando categoria_id a examenes...")
        with db.engine.connect() as conn:
            result = conn.execute(db.text("PRAGMA table_info(examenes)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'categoria_id' not in columns:
                conn.execute(db.text("""
                    ALTER TABLE examenes 
                    ADD COLUMN categoria_id INTEGER
                """))
                conn.commit()
                print("✅ Columna categoria_id agregada a examenes")
            else:
                print("ℹ️  Columna categoria_id ya existe")
        
        # Agregar columnas a preguntas
        print("\n➕ Agregando columnas ICFES a preguntas...")
        with db.engine.connect() as conn:
            result = conn.execute(db.text("PRAGMA table_info(preguntas)"))
            columns = [row[1] for row in result.fetchall()]
            
            nuevas_columnas = {
                'nivel_dificultad': "VARCHAR(20) DEFAULT 'basico'",
                'tiempo_estimado': "INTEGER DEFAULT 60",
                'explicacion': "TEXT",
                'imagen_url': "VARCHAR(255)"
            }
            
            for columna, tipo in nuevas_columnas.items():
                if columna not in columns:
                    print(f"  ➕ Agregando {columna}...")
                    conn.execute(db.text(f"ALTER TABLE preguntas ADD COLUMN {columna} {tipo}"))
                    conn.commit()
                    print(f"  ✅ {columna} agregada")
                else:
                    print(f"  ℹ️  {columna} ya existe")
        
        print("\n✅ Migración ICFES completada exitosamente!")
        print("\n📊 Resumen:")
        print("  - Tabla categorias creada con 6 categorías predefinidas")
        print("  - Exámenes ahora pueden tener categoría")
        print("  - Preguntas incluyen nivel de dificultad, tiempo estimado y explicación")


if __name__ == "__main__":
    migrate()

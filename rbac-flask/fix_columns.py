"""
Migración para verificar y agregar todas las columnas faltantes
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db


def migrate():
    app = create_app()
    
    with app.app_context():
        print("🔍 Verificando columnas en tabla examenes...")
        
        with db.engine.connect() as conn:
            # Verificar columnas existentes
            result = conn.execute(db.text("PRAGMA table_info(examenes)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"📋 Columnas actuales: {columns}")
            
            # Columnas requeridas
            columnas_requeridas = {
                'duracion_minutos': 'INTEGER DEFAULT 60',
                'fecha_limite': 'DATETIME',
                'publicado': 'BOOLEAN DEFAULT 0',
                'intentos_maximos': 'INTEGER DEFAULT 1',
                'mostrar_respuestas': 'BOOLEAN DEFAULT 1',
                'barajar_preguntas': 'BOOLEAN DEFAULT 0',
                'calificacion_minima': 'REAL DEFAULT 60.0',
                'categoria_id': 'INTEGER'
            }
            
            for columna, tipo in columnas_requeridas.items():
                if columna not in columns:
                    print(f"  ➕ Agregando {columna}...")
                    conn.execute(db.text(f"ALTER TABLE examenes ADD COLUMN {columna} {tipo}"))
                    conn.commit()
                    print(f"  ✅ {columna} agregada")
                else:
                    print(f"  ✅ {columna} ya existe")
        
        print("\n🔍 Verificando columnas en tabla preguntas...")
        
        with db.engine.connect() as conn:
            result = conn.execute(db.text("PRAGMA table_info(preguntas)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"📋 Columnas actuales: {columns}")
            
            columnas_requeridas = {
                'nivel_dificultad': "VARCHAR(20) DEFAULT 'basico'",
                'tiempo_estimado': "INTEGER DEFAULT 60",
                'explicacion': "TEXT",
                'imagen_url': "VARCHAR(255)"
            }
            
            for columna, tipo in columnas_requeridas.items():
                if columna not in columns:
                    print(f"  ➕ Agregando {columna}...")
                    conn.execute(db.text(f"ALTER TABLE preguntas ADD COLUMN {columna} {tipo}"))
                    conn.commit()
                    print(f"  ✅ {columna} agregada")
                else:
                    print(f"  ✅ {columna} ya existe")
        
        print("\n✅ Migración completada!")


if __name__ == "__main__":
    migrate()

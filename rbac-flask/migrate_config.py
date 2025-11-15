"""
Migración para agregar campos de configuración avanzada a la tabla examenes
"""
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db

def migrate():
    app = create_app()
    
    with app.app_context():
        # Obtener tipo de base de datos
        engine_name = db.engine.name
        
        print(f"🔍 Base de datos detectada: {engine_name}")
        
        if engine_name == 'sqlite':
            # SQLite
            with db.engine.connect() as conn:
                # Verificar si las columnas ya existen
                result = conn.execute(db.text("PRAGMA table_info(examenes)"))
                columns = [row[1] for row in result.fetchall()]
                
                nuevas_columnas = {
                    'intentos_maximos': 'INTEGER DEFAULT 1',
                    'mostrar_respuestas': 'BOOLEAN DEFAULT 1',
                    'barajar_preguntas': 'BOOLEAN DEFAULT 0',
                    'calificacion_minima': 'REAL DEFAULT 60.0'
                }
                
                for columna, tipo in nuevas_columnas.items():
                    if columna not in columns:
                        print(f"➕ Agregando columna '{columna}'...")
                        conn.execute(db.text(f"ALTER TABLE examenes ADD COLUMN {columna} {tipo}"))
                        conn.commit()
                        print(f"✅ Columna '{columna}' agregada")
                    else:
                        print(f"ℹ️  Columna '{columna}' ya existe")
        
        elif engine_name == 'mysql':
            # MySQL
            with db.engine.connect() as conn:
                # Verificar columnas existentes
                result = conn.execute(db.text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'examenes' 
                    AND TABLE_SCHEMA = DATABASE()
                """))
                columns = [row[0] for row in result.fetchall()]
                
                nuevas_columnas = {
                    'intentos_maximos': 'INT DEFAULT 1',
                    'mostrar_respuestas': 'TINYINT(1) DEFAULT 1',
                    'barajar_preguntas': 'TINYINT(1) DEFAULT 0',
                    'calificacion_minima': 'FLOAT DEFAULT 60.0'
                }
                
                for columna, tipo in nuevas_columnas.items():
                    if columna not in columns:
                        print(f"➕ Agregando columna '{columna}'...")
                        conn.execute(db.text(f"ALTER TABLE examenes ADD COLUMN {columna} {tipo}"))
                        conn.commit()
                        print(f"✅ Columna '{columna}' agregada")
                    else:
                        print(f"ℹ️  Columna '{columna}' ya existe")
        
        print("\n✅ Migración completada exitosamente")

if __name__ == "__main__":
    migrate()

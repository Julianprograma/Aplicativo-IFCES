"""
Script para agregar campos faltantes para funcionalidad de estudiantes
- es_correcta en respuestas
- tiempo_utilizado en examenes_resultados
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Verificar y agregar es_correcta a respuestas
        print("Agregando campo es_correcta a respuestas...")
        db.session.execute(text("""
            ALTER TABLE respuestas 
            ADD COLUMN es_correcta BOOLEAN DEFAULT 0
        """))
        print("✓ Campo es_correcta agregado")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Campo es_correcta ya existe")
        else:
            print(f"Error agregando es_correcta: {e}")
    
    try:
        # Verificar y agregar tiempo_utilizado a examenes_resultados
        print("Agregando campo tiempo_utilizado a examenes_resultados...")
        db.session.execute(text("""
            ALTER TABLE examenes_resultados 
            ADD COLUMN tiempo_utilizado INTEGER DEFAULT 0
        """))
        print("✓ Campo tiempo_utilizado agregado")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Campo tiempo_utilizado ya existe")
        else:
            print(f"Error agregando tiempo_utilizado: {e}")
    
    try:
        db.session.commit()
        print("\n✅ Migración completada exitosamente!")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error al guardar cambios: {e}")

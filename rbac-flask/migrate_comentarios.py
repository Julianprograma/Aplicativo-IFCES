"""
Migración: Agregar comentarios del profesor y fecha_presentacion a ExamenResultado
"""
import sqlite3
from datetime import datetime

def run_migration():
    conn = sqlite3.connect('instance/app.db')
    cursor = conn.cursor()
    
    print("🔍 Verificando columnas en tabla examenes_resultados...")
    cursor.execute("PRAGMA table_info(examenes_resultados)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"📋 Columnas actuales: {columns}")
    
    # Agregar comentario_profesor
    if 'comentario_profesor' not in columns:
        print("➕ Agregando comentario_profesor...")
        cursor.execute("""
            ALTER TABLE examenes_resultados 
            ADD COLUMN comentario_profesor TEXT
        """)
        print("  ✅ comentario_profesor agregada")
    else:
        print("  ✅ comentario_profesor ya existe")
    
    # Agregar recomendaciones
    if 'recomendaciones' not in columns:
        print("➕ Agregando recomendaciones...")
        cursor.execute("""
            ALTER TABLE examenes_resultados 
            ADD COLUMN recomendaciones TEXT
        """)
        print("  ✅ recomendaciones agregada")
    else:
        print("  ✅ recomendaciones ya existe")
    
    # Agregar fecha_presentacion (copiar desde fecha_fin si existe)
    if 'fecha_presentacion' not in columns:
        print("➕ Agregando fecha_presentacion...")
        cursor.execute("""
            ALTER TABLE examenes_resultados 
            ADD COLUMN fecha_presentacion DATETIME
        """)
        # Copiar datos de fecha_fin a fecha_presentacion
        cursor.execute("""
            UPDATE examenes_resultados 
            SET fecha_presentacion = fecha_fin
            WHERE fecha_fin IS NOT NULL
        """)
        print("  ✅ fecha_presentacion agregada")
    else:
        print("  ✅ fecha_presentacion ya existe")
    
    conn.commit()
    conn.close()
    print("✅ Migración completada!")

if __name__ == '__main__':
    run_migration()

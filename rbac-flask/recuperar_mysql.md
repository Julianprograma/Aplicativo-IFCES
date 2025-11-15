# Recuperación de MySQL - Base de Datos Corrupta

## Error Detectado
```
Database page corruption on disk or a failed file read
Log sequence number X is in the future! Current system log sequence number Y
```

## Solución Paso a Paso

### 1. Activar Modo de Recuperación Forzada
Editar `c:\xampp\mysql\bin\my.ini` y agregar en la sección `[mysqld]`:

```ini
innodb_force_recovery = 4
```

### 2. Iniciar MySQL en XAMPP
- Arrancar MySQL desde el panel de control de XAMPP
- Debería iniciar en modo solo lectura

### 3. Exportar Base de Datos
Ejecutar en PowerShell:
```powershell
cd c:\xampp\mysql\bin
.\mysqldump.exe -u root aplicativo_ifces > C:\backup_aplicativo_ifces.sql
```

### 4. Detener MySQL y Eliminar Datos Corruptos
```powershell
# Detener MySQL en XAMPP primero

# Respaldar carpeta data actual
Copy-Item c:\xampp\mysql\data c:\xampp\mysql\data_corrupted_backup -Recurse

# Eliminar archivos InnoDB
Remove-Item c:\xampp\mysql\data\ibdata1 -Force
Remove-Item c:\xampp\mysql\data\ib_logfile* -Force
Remove-Item c:\xampp\mysql\data\ib_buffer_pool -Force
Remove-Item c:\xampp\mysql\data\ibtmp1 -Force -ErrorAction SilentlyContinue

# Eliminar base de datos aplicativo_ifces
Remove-Item c:\xampp\mysql\data\aplicativo_ifces -Recurse -Force
```

### 5. Quitar Modo de Recuperación
Editar `c:\xampp\mysql\bin\my.ini` y **comentar o eliminar**:
```ini
# innodb_force_recovery = 4
```

### 6. Iniciar MySQL Limpio
- Arrancar MySQL en XAMPP
- Debería crear archivos InnoDB nuevos

### 7. Restaurar Base de Datos
```powershell
cd c:\xampp\mysql\bin
.\mysql.exe -u root -e "CREATE DATABASE aplicativo_ifces CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
.\mysql.exe -u root aplicativo_ifces < C:\backup_aplicativo_ifces.sql
```

## Notas Importantes
- **innodb_force_recovery = 4**: Permite lectura pero no escritura
- Si nivel 4 no funciona, probar con nivel 6 (más agresivo)
- El backup en `data_corrupted_backup` se puede eliminar después de verificar que todo funciona
- Si no tienes backup SQL previo, esta es tu última oportunidad de recuperar los datos

## Alternativa Rápida (Si no tienes datos importantes)
Si la base de datos está vacía o en desarrollo:
1. Eliminar carpeta `c:\xampp\mysql\data\aplicativo_ifces`
2. Reiniciar MySQL
3. Ejecutar migraciones: `python migrate_db.py`

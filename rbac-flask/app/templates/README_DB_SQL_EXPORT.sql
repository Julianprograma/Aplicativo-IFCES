-- SQL de exportación rápida para MySQL (phpMyAdmin)
-- Crea la BD y la tabla users compatibles con la aplicación

CREATE DATABASE IF NOT EXISTS `flask_roles` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `flask_roles`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL UNIQUE,
  `email` varchar(120) NOT NULL UNIQUE,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'estudiante',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Nota: crea el primer admin con el comando CLI "flask create-user".

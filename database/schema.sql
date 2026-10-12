-- Schema del database di Barber Booking.
-- Tutte le colonne DATETIME sono in UTC.

CREATE DATABASE IF NOT EXISTS barber_booking
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE barber_booking;

CREATE TABLE utenti (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    nome                VARCHAR(100) NOT NULL,
    cognome             VARCHAR(100) NOT NULL,
    telefono            VARCHAR(20)  NOT NULL,
    ruolo               ENUM('cliente', 'dipendente', 'proprietario') NOT NULL DEFAULT 'cliente',
    riceve_prenotazioni BOOLEAN      NOT NULL DEFAULT FALSE,
    attivo              BOOLEAN      NOT NULL DEFAULT TRUE,
    creato_il           DATETIME     NOT NULL DEFAULT (UTC_TIMESTAMP())
) ENGINE = InnoDB;
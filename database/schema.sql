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

CREATE TABLE servizi (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nome             VARCHAR(100) NOT NULL UNIQUE,
    descrizione      VARCHAR(255) NULL,
    durata_minuti    INT          NOT NULL,
    prezzo_centesimi INT          NOT NULL,
    attivo           BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_servizi_durata CHECK (durata_minuti > 0 AND durata_minuti % 30 = 0),
    CONSTRAINT chk_servizi_prezzo CHECK (prezzo_centesimi >= 0)
) ENGINE = InnoDB;
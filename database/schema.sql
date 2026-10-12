-- Schema del database di Barber Booking.
-- Tutte le colonne DATETIME sono in UTC.
DROP DATABASE IF EXISTS barber_booking;

CREATE DATABASE barber_booking
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

CREATE TABLE prenotazioni (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id         INT      NOT NULL,
    dipendente_id      INT      NOT NULL,
    inizio             DATETIME NOT NULL,
    fine               DATETIME NOT NULL,
    stato              ENUM('in_attesa_pagamento', 'confermata', 'scaduta', 'annullata')
                                NOT NULL DEFAULT 'in_attesa_pagamento',
    modalita_pagamento ENUM('acconto', 'completo') NOT NULL,
    scade_il           DATETIME NOT NULL,
    annullata_il       DATETIME NULL,
    annullata_da       ENUM('cliente', 'salone') NULL,
    creato_il          DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
    CONSTRAINT fk_prenotazioni_cliente    FOREIGN KEY (cliente_id)    REFERENCES utenti (id),
    CONSTRAINT fk_prenotazioni_dipendente FOREIGN KEY (dipendente_id) REFERENCES utenti (id),
    CONSTRAINT chk_prenotazioni_orario    CHECK (fine > inizio),
    INDEX idx_prenotazioni_dipendente_inizio (dipendente_id, inizio),
    INDEX idx_prenotazioni_cliente (cliente_id)
) ENGINE = InnoDB;

CREATE TABLE prenotazioni_servizi (
    prenotazione_id  INT NOT NULL,
    servizio_id      INT NOT NULL,
    durata_minuti    INT NOT NULL,
    prezzo_centesimi INT NOT NULL,
    PRIMARY KEY (prenotazione_id, servizio_id),
    CONSTRAINT fk_prenotazioni_servizi_prenotazione FOREIGN KEY (prenotazione_id) REFERENCES prenotazioni (id),
    CONSTRAINT fk_prenotazioni_servizi_servizio     FOREIGN KEY (servizio_id)     REFERENCES servizi (id)
) ENGINE = InnoDB;

CREATE TABLE orari_settimanali (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    giorno_settimana TINYINT NOT NULL,
    ora_inizio       TIME    NOT NULL,
    ora_fine         TIME    NOT NULL,
    CONSTRAINT chk_orari_settimanali_giorno CHECK (giorno_settimana BETWEEN 1 AND 7),
    CONSTRAINT chk_orari_settimanali_turno  CHECK (ora_fine > ora_inizio)
) ENGINE = InnoDB;

CREATE TABLE eccezioni_date (
    data   DATE         PRIMARY KEY,
    aperto BOOLEAN      NOT NULL,
    nota   VARCHAR(255) NULL
) ENGINE = InnoDB;
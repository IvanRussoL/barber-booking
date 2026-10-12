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

CREATE TABLE eccezioni_turni (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    data       DATE NOT NULL,
    ora_inizio TIME NOT NULL,
    ora_fine   TIME NOT NULL,
    CONSTRAINT fk_eccezioni_turni_data FOREIGN KEY (data) REFERENCES eccezioni_date (data) ON DELETE CASCADE,
    CONSTRAINT chk_eccezioni_turni_turno CHECK (ora_fine > ora_inizio)
) ENGINE = InnoDB;

CREATE TABLE indisponibilita (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    dipendente_id INT          NULL,
    inizio        DATETIME     NOT NULL,
    fine          DATETIME     NOT NULL,
    nota          VARCHAR(255) NULL,
    CONSTRAINT fk_indisponibilita_dipendente FOREIGN KEY (dipendente_id) REFERENCES utenti (id),
    CONSTRAINT chk_indisponibilita_periodo   CHECK (fine > inizio),
    INDEX idx_indisponibilita_dipendente_inizio (dipendente_id, inizio)
) ENGINE = InnoDB;

CREATE TABLE impostazioni (
    id                  TINYINT      PRIMARY KEY,
    nome_salone         VARCHAR(100) NOT NULL,
    indirizzo           VARCHAR(255) NOT NULL,
    telefono            VARCHAR(20)  NOT NULL,
    fuso_orario         VARCHAR(64)  NOT NULL DEFAULT 'Europe/Rome',
    latitudine          DECIMAL(9,6) NOT NULL,
    longitudine         DECIMAL(9,6) NOT NULL,
    percentuale_acconto TINYINT      NOT NULL,
    mesi_prenotabili    TINYINT      NOT NULL DEFAULT 3,
    CONSTRAINT chk_impostazioni_riga_unica CHECK (id = 1),
    CONSTRAINT chk_impostazioni_acconto    CHECK (percentuale_acconto BETWEEN 1 AND 99),
    CONSTRAINT chk_impostazioni_mesi       CHECK (mesi_prenotabili BETWEEN 0 AND 3)
) ENGINE = InnoDB;

CREATE TABLE eventi (
    id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    tipo      VARCHAR(50)  NOT NULL,
    pagina    VARCHAR(255) NOT NULL,
    elemento  VARCHAR(100) NULL,
    sessione  VARCHAR(64)  NOT NULL,
    creato_il DATETIME     NOT NULL DEFAULT (UTC_TIMESTAMP()),
    INDEX idx_eventi_tipo_creato_il (tipo, creato_il)
) ENGINE = InnoDB;

CREATE TABLE prodotti (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nome             VARCHAR(100) NOT NULL UNIQUE,
    descrizione      VARCHAR(255) NULL,
    foto             VARCHAR(100) NULL,
    prezzo_centesimi INT          NOT NULL,
    disponibile      BOOLEAN      NOT NULL DEFAULT TRUE,
    attivo           BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_prodotti_prezzo CHECK (prezzo_centesimi > 0)
) ENGINE = InnoDB;

-- Dati iniziali necessari al funzionamento, modificabili dal proprietario.

INSERT INTO impostazioni (id, nome_salone, indirizzo, telefono, latitudine, longitudine, percentuale_acconto)
VALUES (1, 'Barber Booking', 'Indirizzo da impostare', '+390000000000', 0, 0, 30);

-- Calendario di partenza: lunedì chiuso, dal martedì alla domenica 09:00-13:00 e 15:00-23:00.
INSERT INTO orari_settimanali (giorno_settimana, ora_inizio, ora_fine) VALUES
    (2, '09:00', '13:00'), (2, '15:00', '23:00'),
    (3, '09:00', '13:00'), (3, '15:00', '23:00'),
    (4, '09:00', '13:00'), (4, '15:00', '23:00'),
    (5, '09:00', '13:00'), (5, '15:00', '23:00'),
    (6, '09:00', '13:00'), (6, '15:00', '23:00'),
    (7, '09:00', '13:00'), (7, '15:00', '23:00');
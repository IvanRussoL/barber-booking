-- Schema del database di Barber Booking.
-- Tutte le colonne DATETIME sono in UTC.
-- Più saloni nello stesso sito: i dati di ogni salone hanno la colonna salone_id.
DROP DATABASE IF EXISTS barber_booking;

CREATE DATABASE barber_booking
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE barber_booking;

-- Province italiane (dati ISTAT): servono a cercare i saloni per regione e provincia.
CREATE TABLE province (
    sigla   CHAR(2)      PRIMARY KEY,
    nome    VARCHAR(100) NOT NULL,
    regione VARCHAR(50)  NOT NULL,
    INDEX idx_province_regione (regione)
) ENGINE = InnoDB;

-- Un salone per riga: dati pubblici, posizione e regole di prenotazione.
CREATE TABLE saloni (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    nome                VARCHAR(100) NOT NULL,
    indirizzo           VARCHAR(255) NOT NULL,
    provincia           CHAR(2)      NOT NULL,
    telefono            VARCHAR(20)  NOT NULL,
    fuso_orario         VARCHAR(64)  NOT NULL DEFAULT 'Europe/Rome',
    latitudine          DECIMAL(9,6) NOT NULL,
    longitudine         DECIMAL(9,6) NOT NULL,
    percentuale_acconto TINYINT      NOT NULL DEFAULT 30,
    mesi_prenotabili    TINYINT      NOT NULL DEFAULT 3,
    attivo              BOOLEAN      NOT NULL DEFAULT TRUE,
    creato_il           DATETIME     NOT NULL DEFAULT (UTC_TIMESTAMP()),
    CONSTRAINT fk_saloni_provincia    FOREIGN KEY (provincia) REFERENCES province (sigla),
    CONSTRAINT chk_saloni_latitudine  CHECK (latitudine BETWEEN -90 AND 90),
    CONSTRAINT chk_saloni_longitudine CHECK (longitudine BETWEEN -180 AND 180),
    CONSTRAINT chk_saloni_acconto     CHECK (percentuale_acconto BETWEEN 1 AND 99),
    CONSTRAINT chk_saloni_mesi        CHECK (mesi_prenotabili BETWEEN 0 AND 3),
    INDEX idx_saloni_provincia (provincia)
) ENGINE = InnoDB;

-- I clienti non appartengono a un salone (prenotano dove vogliono); dipendenti e proprietari sì.
CREATE TABLE utenti (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    nome                VARCHAR(100) NOT NULL,
    cognome             VARCHAR(100) NOT NULL,
    telefono            VARCHAR(20)  NOT NULL,
    ruolo               ENUM('cliente', 'dipendente', 'proprietario') NOT NULL DEFAULT 'cliente',
    salone_id           INT          NULL,
    riceve_prenotazioni BOOLEAN      NOT NULL DEFAULT FALSE,
    attivo              BOOLEAN      NOT NULL DEFAULT TRUE,
    creato_il           DATETIME     NOT NULL DEFAULT (UTC_TIMESTAMP()),
    CONSTRAINT fk_utenti_salone FOREIGN KEY (salone_id) REFERENCES saloni (id),
    CONSTRAINT chk_utenti_salone CHECK (
        (ruolo = 'cliente' AND salone_id IS NULL) OR (ruolo <> 'cliente' AND salone_id IS NOT NULL)
    )
) ENGINE = InnoDB;

CREATE TABLE servizi (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    salone_id        INT          NOT NULL,
    nome             VARCHAR(100) NOT NULL,
    descrizione      VARCHAR(255) NULL,
    durata_minuti    INT          NOT NULL,
    prezzo_centesimi INT          NOT NULL,
    attivo           BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_servizi_salone  FOREIGN KEY (salone_id) REFERENCES saloni (id),
    CONSTRAINT uq_servizi_nome    UNIQUE (salone_id, nome),
    CONSTRAINT chk_servizi_durata CHECK (durata_minuti > 0 AND durata_minuti % 30 = 0),
    CONSTRAINT chk_servizi_prezzo CHECK (prezzo_centesimi >= 0)
) ENGINE = InnoDB;

CREATE TABLE prenotazioni (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    salone_id          INT      NOT NULL,
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
    CONSTRAINT fk_prenotazioni_salone     FOREIGN KEY (salone_id)     REFERENCES saloni (id),
    CONSTRAINT fk_prenotazioni_cliente    FOREIGN KEY (cliente_id)    REFERENCES utenti (id),
    CONSTRAINT fk_prenotazioni_dipendente FOREIGN KEY (dipendente_id) REFERENCES utenti (id),
    CONSTRAINT chk_prenotazioni_orario    CHECK (fine > inizio),
    INDEX idx_prenotazioni_dipendente_inizio (dipendente_id, inizio),
    INDEX idx_prenotazioni_salone_inizio (salone_id, inizio),
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
    salone_id        INT     NOT NULL,
    giorno_settimana TINYINT NOT NULL,
    ora_inizio       TIME    NOT NULL,
    ora_fine         TIME    NOT NULL,
    CONSTRAINT fk_orari_settimanali_salone  FOREIGN KEY (salone_id) REFERENCES saloni (id),
    CONSTRAINT chk_orari_settimanali_giorno CHECK (giorno_settimana BETWEEN 1 AND 7),
    CONSTRAINT chk_orari_settimanali_turno  CHECK (ora_fine > ora_inizio),
    INDEX idx_orari_settimanali_salone_giorno (salone_id, giorno_settimana)
) ENGINE = InnoDB;

CREATE TABLE eccezioni_date (
    salone_id INT          NOT NULL,
    data      DATE         NOT NULL,
    aperto    BOOLEAN      NOT NULL,
    nota      VARCHAR(255) NULL,
    PRIMARY KEY (salone_id, data),
    CONSTRAINT fk_eccezioni_date_salone FOREIGN KEY (salone_id) REFERENCES saloni (id)
) ENGINE = InnoDB;

CREATE TABLE eccezioni_turni (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    salone_id  INT  NOT NULL,
    data       DATE NOT NULL,
    ora_inizio TIME NOT NULL,
    ora_fine   TIME NOT NULL,
    CONSTRAINT fk_eccezioni_turni_data FOREIGN KEY (salone_id, data)
        REFERENCES eccezioni_date (salone_id, data) ON DELETE CASCADE,
    CONSTRAINT chk_eccezioni_turni_turno CHECK (ora_fine > ora_inizio)
) ENGINE = InnoDB;

-- Assenza di un dipendente, oppure chiusura dell'intero salone (dipendente_id NULL).
CREATE TABLE indisponibilita (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    salone_id     INT          NOT NULL,
    dipendente_id INT          NULL,
    inizio        DATETIME     NOT NULL,
    fine          DATETIME     NOT NULL,
    nota          VARCHAR(255) NULL,
    CONSTRAINT fk_indisponibilita_salone     FOREIGN KEY (salone_id)     REFERENCES saloni (id),
    CONSTRAINT fk_indisponibilita_dipendente FOREIGN KEY (dipendente_id) REFERENCES utenti (id),
    CONSTRAINT chk_indisponibilita_periodo   CHECK (fine > inizio),
    INDEX idx_indisponibilita_salone_inizio (salone_id, inizio),
    INDEX idx_indisponibilita_dipendente_inizio (dipendente_id, inizio)
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
    salone_id        INT          NOT NULL,
    nome             VARCHAR(100) NOT NULL,
    descrizione      VARCHAR(255) NULL,
    foto             VARCHAR(100) NULL,
    prezzo_centesimi INT          NOT NULL,
    disponibile      BOOLEAN      NOT NULL DEFAULT TRUE,
    attivo           BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_prodotti_salone  FOREIGN KEY (salone_id) REFERENCES saloni (id),
    CONSTRAINT uq_prodotti_nome    UNIQUE (salone_id, nome),
    CONSTRAINT chk_prodotti_prezzo CHECK (prezzo_centesimi > 0)
) ENGINE = InnoDB;

CREATE TABLE ordini (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    salone_id    INT      NOT NULL,
    cliente_id   INT      NOT NULL,
    stato        ENUM('in_attesa_pagamento', 'confermato', 'ritirato', 'scaduto', 'annullato')
                          NOT NULL DEFAULT 'in_attesa_pagamento',
    scade_il     DATETIME NOT NULL,
    ritirato_il  DATETIME NULL,
    annullato_il DATETIME NULL,
    creato_il    DATETIME NOT NULL DEFAULT (UTC_TIMESTAMP()),
    CONSTRAINT fk_ordini_salone  FOREIGN KEY (salone_id)  REFERENCES saloni (id),
    CONSTRAINT fk_ordini_cliente FOREIGN KEY (cliente_id) REFERENCES utenti (id),
    INDEX idx_ordini_cliente (cliente_id),
    INDEX idx_ordini_stato (stato)
) ENGINE = InnoDB;

CREATE TABLE ordini_prodotti (
    ordine_id        INT NOT NULL,
    prodotto_id      INT NOT NULL,
    quantita         INT NOT NULL,
    prezzo_centesimi INT NOT NULL,
    PRIMARY KEY (ordine_id, prodotto_id),
    CONSTRAINT fk_ordini_prodotti_ordine   FOREIGN KEY (ordine_id)   REFERENCES ordini (id),
    CONSTRAINT fk_ordini_prodotti_prodotto FOREIGN KEY (prodotto_id) REFERENCES prodotti (id),
    CONSTRAINT chk_ordini_prodotti_quantita CHECK (quantita BETWEEN 1 AND 10)
) ENGINE = InnoDB;

CREATE TABLE pagamenti (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    prenotazione_id      INT          NULL,
    ordine_id            INT          NULL,
    tipo                 ENUM('online', 'in_sede', 'rimborso') NOT NULL,
    importo_centesimi    INT          NOT NULL,
    stato                ENUM('in_attesa', 'completato', 'fallito') NOT NULL DEFAULT 'in_attesa',
    riferimento_provider VARCHAR(255) NULL UNIQUE,
    creato_il            DATETIME     NOT NULL DEFAULT (UTC_TIMESTAMP()),
    CONSTRAINT fk_pagamenti_prenotazione FOREIGN KEY (prenotazione_id) REFERENCES prenotazioni (id),
    CONSTRAINT fk_pagamenti_ordine       FOREIGN KEY (ordine_id)       REFERENCES ordini (id),
    CONSTRAINT chk_pagamenti_importo     CHECK (importo_centesimi > 0),
    CONSTRAINT chk_pagamenti_riferimento CHECK (
        (prenotazione_id IS NOT NULL AND ordine_id IS NULL)
        OR (prenotazione_id IS NULL AND ordine_id IS NOT NULL)
    ),
    CONSTRAINT chk_pagamenti_in_sede     CHECK (tipo <> 'in_sede' OR prenotazione_id IS NOT NULL)
) ENGINE = InnoDB;

-- Una recensione per appuntamento svolto: solo chi è stato nel salone può recensirlo.
CREATE TABLE recensioni (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    prenotazione_id INT          NOT NULL UNIQUE,
    salone_id       INT          NOT NULL,
    cliente_id      INT          NOT NULL,
    voto            TINYINT      NOT NULL,
    commento        VARCHAR(500) NULL,
    creato_il       DATETIME     NOT NULL DEFAULT (UTC_TIMESTAMP()),
    CONSTRAINT fk_recensioni_prenotazione FOREIGN KEY (prenotazione_id) REFERENCES prenotazioni (id),
    CONSTRAINT fk_recensioni_salone       FOREIGN KEY (salone_id)       REFERENCES saloni (id),
    CONSTRAINT fk_recensioni_cliente      FOREIGN KEY (cliente_id)      REFERENCES utenti (id),
    CONSTRAINT chk_recensioni_voto        CHECK (voto BETWEEN 1 AND 5),
    INDEX idx_recensioni_salone_creato_il (salone_id, creato_il)
) ENGINE = InnoDB;

-- Province italiane (110), ricavate dall'elenco dei comuni ISTAT pubblicato dal progetto comuni-json
-- (scaricato il 14/10/2026). Le 8 province della Sardegna sono quelle in vigore dal 2026 (riforma regionale),
-- prese dall'elenco ISTAT fornito a parte: comuni-json aveva ancora le 5 precedenti.
INSERT INTO province (sigla, nome, regione) VALUES
    ('CH', 'Chieti', 'Abruzzo'),
    ('AQ', 'L''Aquila', 'Abruzzo'),
    ('PE', 'Pescara', 'Abruzzo'),
    ('TE', 'Teramo', 'Abruzzo'),
    ('MT', 'Matera', 'Basilicata'),
    ('PZ', 'Potenza', 'Basilicata'),
    ('CZ', 'Catanzaro', 'Calabria'),
    ('CS', 'Cosenza', 'Calabria'),
    ('KR', 'Crotone', 'Calabria'),
    ('RC', 'Reggio Calabria', 'Calabria'),
    ('VV', 'Vibo Valentia', 'Calabria'),
    ('AV', 'Avellino', 'Campania'),
    ('BN', 'Benevento', 'Campania'),
    ('CE', 'Caserta', 'Campania'),
    ('NA', 'Napoli', 'Campania'),
    ('SA', 'Salerno', 'Campania'),
    ('BO', 'Bologna', 'Emilia-Romagna'),
    ('FE', 'Ferrara', 'Emilia-Romagna'),
    ('FC', 'Forlì-Cesena', 'Emilia-Romagna'),
    ('MO', 'Modena', 'Emilia-Romagna'),
    ('PR', 'Parma', 'Emilia-Romagna'),
    ('PC', 'Piacenza', 'Emilia-Romagna'),
    ('RA', 'Ravenna', 'Emilia-Romagna'),
    ('RE', 'Reggio nell''Emilia', 'Emilia-Romagna'),
    ('RN', 'Rimini', 'Emilia-Romagna'),
    ('GO', 'Gorizia', 'Friuli-Venezia Giulia'),
    ('PN', 'Pordenone', 'Friuli-Venezia Giulia'),
    ('TS', 'Trieste', 'Friuli-Venezia Giulia'),
    ('UD', 'Udine', 'Friuli-Venezia Giulia'),
    ('FR', 'Frosinone', 'Lazio'),
    ('LT', 'Latina', 'Lazio'),
    ('RI', 'Rieti', 'Lazio'),
    ('RM', 'Roma', 'Lazio'),
    ('VT', 'Viterbo', 'Lazio'),
    ('GE', 'Genova', 'Liguria'),
    ('IM', 'Imperia', 'Liguria'),
    ('SP', 'La Spezia', 'Liguria'),
    ('SV', 'Savona', 'Liguria'),
    ('BG', 'Bergamo', 'Lombardia'),
    ('BS', 'Brescia', 'Lombardia'),
    ('CO', 'Como', 'Lombardia'),
    ('CR', 'Cremona', 'Lombardia'),
    ('LC', 'Lecco', 'Lombardia'),
    ('LO', 'Lodi', 'Lombardia'),
    ('MN', 'Mantova', 'Lombardia'),
    ('MI', 'Milano', 'Lombardia'),
    ('MB', 'Monza e della Brianza', 'Lombardia'),
    ('PV', 'Pavia', 'Lombardia'),
    ('SO', 'Sondrio', 'Lombardia'),
    ('VA', 'Varese', 'Lombardia'),
    ('AN', 'Ancona', 'Marche'),
    ('AP', 'Ascoli Piceno', 'Marche'),
    ('FM', 'Fermo', 'Marche'),
    ('MC', 'Macerata', 'Marche'),
    ('PU', 'Pesaro e Urbino', 'Marche'),
    ('CB', 'Campobasso', 'Molise'),
    ('IS', 'Isernia', 'Molise'),
    ('AL', 'Alessandria', 'Piemonte'),
    ('AT', 'Asti', 'Piemonte'),
    ('BI', 'Biella', 'Piemonte'),
    ('CN', 'Cuneo', 'Piemonte'),
    ('NO', 'Novara', 'Piemonte'),
    ('TO', 'Torino', 'Piemonte'),
    ('VB', 'Verbano-Cusio-Ossola', 'Piemonte'),
    ('VC', 'Vercelli', 'Piemonte'),
    ('BA', 'Bari', 'Puglia'),
    ('BT', 'Barletta-Andria-Trani', 'Puglia'),
    ('BR', 'Brindisi', 'Puglia'),
    ('FG', 'Foggia', 'Puglia'),
    ('LE', 'Lecce', 'Puglia'),
    ('TA', 'Taranto', 'Puglia'),
    ('CA', 'Cagliari', 'Sardegna'),
    ('OT', 'Gallura Nord-Est Sardegna', 'Sardegna'),
    ('VS', 'Medio Campidano', 'Sardegna'),
    ('NU', 'Nuoro', 'Sardegna'),
    ('OG', 'Ogliastra', 'Sardegna'),
    ('OR', 'Oristano', 'Sardegna'),
    ('SS', 'Sassari', 'Sardegna'),
    ('SU', 'Sulcis Iglesiente', 'Sardegna'),
    ('AG', 'Agrigento', 'Sicilia'),
    ('CL', 'Caltanissetta', 'Sicilia'),
    ('CT', 'Catania', 'Sicilia'),
    ('EN', 'Enna', 'Sicilia'),
    ('ME', 'Messina', 'Sicilia'),
    ('PA', 'Palermo', 'Sicilia'),
    ('RG', 'Ragusa', 'Sicilia'),
    ('SR', 'Siracusa', 'Sicilia'),
    ('TP', 'Trapani', 'Sicilia'),
    ('AR', 'Arezzo', 'Toscana'),
    ('FI', 'Firenze', 'Toscana'),
    ('GR', 'Grosseto', 'Toscana'),
    ('LI', 'Livorno', 'Toscana'),
    ('LU', 'Lucca', 'Toscana'),
    ('MS', 'Massa-Carrara', 'Toscana'),
    ('PI', 'Pisa', 'Toscana'),
    ('PT', 'Pistoia', 'Toscana'),
    ('PO', 'Prato', 'Toscana'),
    ('SI', 'Siena', 'Toscana'),
    ('BZ', 'Bolzano/Bozen', 'Trentino-Alto Adige/Südtirol'),
    ('TN', 'Trento', 'Trentino-Alto Adige/Südtirol'),
    ('PG', 'Perugia', 'Umbria'),
    ('TR', 'Terni', 'Umbria'),
    ('AO', 'Valle d''Aosta/Vallée d''Aoste', 'Valle d''Aosta/Vallée d''Aoste'),
    ('BL', 'Belluno', 'Veneto'),
    ('PD', 'Padova', 'Veneto'),
    ('RO', 'Rovigo', 'Veneto'),
    ('TV', 'Treviso', 'Veneto'),
    ('VE', 'Venezia', 'Veneto'),
    ('VR', 'Verona', 'Veneto'),
    ('VI', 'Vicenza', 'Veneto');

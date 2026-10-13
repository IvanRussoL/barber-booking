from datetime import datetime

from app.modelli.prenotazione import Prenotazione, ServizioPrenotato

_SELECT = (
    "SELECT id, cliente_id, dipendente_id, inizio, fine, modalita_pagamento, scade_il, stato, "
    "annullata_il, annullata_da, creato_il FROM prenotazioni "
)


class PrenotazioneRepository:
    """
    Accesso alle tabelle prenotazioni e prenotazioni_servizi.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, prenotazione: Prenotazione) -> int:
        """
        Inserisce la prenotazione e i suoi servizi, senza fare commit.
        Args: prenotazione senza id, con la lista dei ServizioPrenotato.
        Returns: l'id assegnato da MySQL.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO prenotazioni (cliente_id, dipendente_id, inizio, fine, stato, "
                "modalita_pagamento, scade_il) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (prenotazione.cliente_id, prenotazione.dipendente_id, prenotazione.inizio,
                 prenotazione.fine, prenotazione.stato, prenotazione.modalita_pagamento,
                 prenotazione.scade_il),
            )
            prenotazione_id = cur.lastrowid
            cur.executemany(
                "INSERT INTO prenotazioni_servizi (prenotazione_id, servizio_id, durata_minuti, "
                "prezzo_centesimi) VALUES (%s, %s, %s, %s)",
                [(prenotazione_id, s.servizio_id, s.durata_minuti, s.prezzo_centesimi)
                 for s in prenotazione.servizi],
            )
        return prenotazione_id

    def leggi_per_id(self, prenotazione_id: int) -> Prenotazione | None:
        """
        Legge una prenotazione con i suoi servizi (nome letto da servizi, durata e prezzo dalla copia).
        Returns: la Prenotazione, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE id = %s", (prenotazione_id,))
            riga = cur.fetchone()
            if riga is None:
                return None
            cur.execute(
                "SELECT ps.prenotazione_id, ps.servizio_id, s.nome, ps.durata_minuti, ps.prezzo_centesimi "
                "FROM prenotazioni_servizi ps JOIN servizi s ON s.id = ps.servizio_id "
                "WHERE ps.prenotazione_id = %s ORDER BY s.nome",
                (prenotazione_id,),
            )
            servizi = [ServizioPrenotato(**r) for r in cur.fetchall()]
        return Prenotazione(**riga, servizi=servizi)

    def intervalli_occupati(self, dipendente_id: int, da: datetime, a: datetime,
                            adesso: datetime) -> list[tuple[datetime, datetime]]:
        """
        Legge gli appuntamenti del dipendente che toccano [da, a): confermati, oppure in attesa
        di pagamento e non ancora scaduti (bloccano lo slot per 30 minuti).
        Args: date e ore in UTC.
        Returns: lista di coppie (inizio, fine) in UTC.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT inizio, fine FROM prenotazioni WHERE dipendente_id = %s "
                "AND inizio < %s AND fine > %s "
                "AND (stato = 'confermata' OR (stato = 'in_attesa_pagamento' AND scade_il > %s))",
                (dipendente_id, a, da, adesso),
            )
            return cur.fetchall()

    def segna_scadute(self, adesso: datetime) -> None:
        """
        Porta a 'scaduta' le prenotazioni in attesa di pagamento oltre la scadenza, senza fare commit.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE prenotazioni SET stato = 'scaduta' "
                "WHERE stato = 'in_attesa_pagamento' AND scade_il <= %s",
                (adesso,),
            )

    def aggiorna_stato(self, prenotazione_id: int, stato: str,
                       annullata_il: datetime | None = None, annullata_da: str | None = None) -> None:
        """
        Cambia lo stato di una prenotazione, senza fare commit.
        Args: annullata_il e annullata_da solo quando lo stato diventa 'annullata'.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE prenotazioni SET stato = %s, annullata_il = %s, annullata_da = %s WHERE id = %s",
                (stato, annullata_il, annullata_da, prenotazione_id),
            )

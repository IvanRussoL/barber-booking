from datetime import datetime

from app.modelli.indisponibilita import Indisponibilita


class IndisponibilitaRepository:
    """
    Accesso alla tabella indisponibilita: assenze dei dipendenti e chiusure del salone.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def periodi_sovrapposti(self, salone_id: int, dipendente_id: int,
                            da: datetime, a: datetime) -> list[tuple[datetime, datetime]]:
        """
        Legge le assenze del dipendente e le chiusure del suo salone che toccano l'intervallo [da, a).
        Args: date e ore in UTC.
        Returns: lista di coppie (inizio, fine) in UTC.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT inizio, fine FROM indisponibilita "
                "WHERE salone_id = %s AND (dipendente_id = %s OR dipendente_id IS NULL) "
                "AND inizio < %s AND fine > %s",
                (salone_id, dipendente_id, a, da),
            )
            return cur.fetchall()

    def inserisci(self, periodo: Indisponibilita) -> int:
        """
        Inserisce un'assenza (dipendente_id) o una chiusura del salone (dipendente_id None), senza fare commit.
        Returns: l'id assegnato da MySQL.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO indisponibilita (salone_id, dipendente_id, inizio, fine, nota) VALUES (%s, %s, %s, %s, %s)",
                (periodo.salone_id, periodo.dipendente_id, periodo.inizio, periodo.fine, periodo.nota),
            )
            return cur.lastrowid

    def elenca_dal(self, salone_id: int, da: datetime) -> list[Indisponibilita]:
        """
        Assenze e chiusure del salone che finiscono dopo il momento indicato, in ordine di inizio.
        Args: da, in UTC.
        Returns: la lista delle Indisponibilita.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id, salone_id, dipendente_id, inizio, fine, nota FROM indisponibilita "
                "WHERE salone_id = %s AND fine > %s ORDER BY inizio",
                (salone_id, da),
            )
            return [Indisponibilita(**riga) for riga in cur.fetchall()]

    def elimina(self, salone_id: int, periodo_id: int) -> bool:
        """
        Cancella un periodo del salone, senza fare commit. Il salone è nella WHERE: un id di un altro
        salone non cancella niente.
        Returns: True se una riga è stata cancellata.
        """
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM indisponibilita WHERE id = %s AND salone_id = %s", (periodo_id, salone_id))
            return cur.rowcount == 1

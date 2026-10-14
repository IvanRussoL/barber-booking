from datetime import datetime


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

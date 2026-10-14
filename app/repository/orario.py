from datetime import date, datetime, time, timedelta

from app.modelli.orario import EccezioneData, Turno


def _ora(valore: timedelta) -> time:
    """
    Converte una colonna TIME, che il driver restituisce come timedelta, in un orario (time).
    """
    return (datetime.min + valore).time()


def _turni(righe: list[dict]) -> list[Turno]:
    """
    Trasforma le righe con ora_inizio e ora_fine in oggetti Turno.
    """
    return [Turno(_ora(riga["ora_inizio"]), _ora(riga["ora_fine"])) for riga in righe]


class OrarioRepository:
    """
    Accesso al calendario di un salone: orari_settimanali, eccezioni_date ed eccezioni_turni.
    Ogni metodo riceve il salone: gli orari di un salone non si mescolano con quelli di un altro.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def turni_settimanali(self, salone_id: int, giorno_settimana: int) -> list[Turno]:
        """
        Legge i turni di un giorno della settimana, in ordine di inizio.
        Args: giorno_settimana da 1 (lunedì) a 7 (domenica), come date.isoweekday().
        Returns: la lista dei Turni, vuota se il salone è chiuso.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT ora_inizio, ora_fine FROM orari_settimanali "
                "WHERE salone_id = %s AND giorno_settimana = %s ORDER BY ora_inizio",
                (salone_id, giorno_settimana),
            )
            return _turni(cur.fetchall())

    def inserisci_turno_settimanale(self, salone_id: int, giorno_settimana: int, turno: Turno) -> None:
        """
        Aggiunge un turno al calendario settimanale (usato alla creazione del salone), senza fare commit.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orari_settimanali (salone_id, giorno_settimana, ora_inizio, ora_fine) "
                "VALUES (%s, %s, %s, %s)",
                (salone_id, giorno_settimana, turno.ora_inizio, turno.ora_fine),
            )

    def sostituisci_turni_settimanali(self, salone_id: int, giorno_settimana: int, turni: list[Turno]) -> None:
        """
        Sostituisce i turni di un giorno della settimana (nessun turno: salone chiuso quel giorno),
        senza fare commit.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM orari_settimanali WHERE salone_id = %s AND giorno_settimana = %s",
                (salone_id, giorno_settimana),
            )
            cur.executemany(
                "INSERT INTO orari_settimanali (salone_id, giorno_settimana, ora_inizio, ora_fine) "
                "VALUES (%s, %s, %s, %s)",
                [(salone_id, giorno_settimana, turno.ora_inizio, turno.ora_fine) for turno in turni],
            )

    def leggi_eccezione(self, salone_id: int, giorno: date) -> EccezioneData | None:
        """
        Legge l'eccezione di una data, con i suoi turni se il salone è aperto.
        Returns: l'EccezioneData, oppure None se per quella data vale il calendario settimanale.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT data, aperto, nota FROM eccezioni_date WHERE salone_id = %s AND data = %s",
                (salone_id, giorno),
            )
            riga = cur.fetchone()
            if riga is None:
                return None
            cur.execute(
                "SELECT ora_inizio, ora_fine FROM eccezioni_turni WHERE salone_id = %s AND data = %s "
                "ORDER BY ora_inizio",
                (salone_id, giorno),
            )
            turni = _turni(cur.fetchall())
        return EccezioneData(riga["data"], bool(riga["aperto"]), turni, riga["nota"])

    def elenca_eccezioni(self, salone_id: int, da: date, a: date) -> list[EccezioneData]:
        """
        Eccezioni del salone con data in [da, a], con i loro turni, in ordine di data.
        Returns: la lista delle EccezioneData.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT data FROM eccezioni_date WHERE salone_id = %s AND data BETWEEN %s AND %s ORDER BY data",
                (salone_id, da, a),
            )
            date_trovate = [riga["data"] for riga in cur.fetchall()]
        return [self.leggi_eccezione(salone_id, giorno) for giorno in date_trovate]

    def salva_eccezione(self, salone_id: int, eccezione: EccezioneData) -> None:
        """
        Salva l'eccezione di una data sostituendo quella precedente, senza fare commit.
        La DELETE cancella anche i vecchi turni grazie a ON DELETE CASCADE.
        """
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM eccezioni_date WHERE salone_id = %s AND data = %s", (salone_id, eccezione.data))
            cur.execute(
                "INSERT INTO eccezioni_date (salone_id, data, aperto, nota) VALUES (%s, %s, %s, %s)",
                (salone_id, eccezione.data, eccezione.aperto, eccezione.nota),
            )
            cur.executemany(
                "INSERT INTO eccezioni_turni (salone_id, data, ora_inizio, ora_fine) VALUES (%s, %s, %s, %s)",
                [(salone_id, eccezione.data, turno.ora_inizio, turno.ora_fine) for turno in eccezione.turni],
            )

    def elimina_eccezione(self, salone_id: int, giorno: date) -> None:
        """
        Toglie l'eccezione di una data (torna a valere il calendario settimanale), senza fare commit.
        """
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM eccezioni_date WHERE salone_id = %s AND data = %s", (salone_id, giorno))

from app.modelli.salone import Provincia


class ProvinciaRepository:
    """
    Accesso alla tabella province (dati ISTAT, solo lettura).
    """

    def __init__(self, connessione):
        self._conn = connessione

    def elenca(self) -> list[Provincia]:
        """
        Tutte le province, ordinate per regione e per nome.
        Returns: la lista delle Province.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT sigla, nome, regione FROM province ORDER BY regione, nome")
            return [Provincia(**riga) for riga in cur.fetchall()]

    def leggi(self, sigla: str) -> Provincia | None:
        """
        Legge una provincia dalla sigla.
        Returns: la Provincia, oppure None se la sigla non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT sigla, nome, regione FROM province WHERE sigla = %s", (sigla,))
            riga = cur.fetchone()
        return Provincia(**riga) if riga else None

    def regioni(self) -> list[str]:
        """
        Le regioni italiane in ordine alfabetico.
        """
        with self._conn.cursor() as cur:
            cur.execute("SELECT DISTINCT regione FROM province ORDER BY regione")
            return [riga[0] for riga in cur.fetchall()]

from app.modelli.servizio import Servizio

_SELECT = "SELECT id, nome, descrizione, durata_minuti, prezzo_centesimi, attivo FROM servizi "

def _da_riga(riga: dict) -> Servizio:
    """
    Trasforma una riga di servizi in un oggetto Servizio, convertendo attivo da 0/1 a bool.
    """
    riga["attivo"] = bool(riga["attivo"])
    return Servizio(**riga)

class ServizioRepository:
    """
    Accesso alla tabella servizi
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, servizio: Servizio) -> int:
        """
        Inserisce un nuovo servizio, senza fare commit.
        Args: servizio senza id.
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se il nome esiste già.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO servizi (nome, descrizione, durata_minuti, prezzo_centesimi, attivo) "
                "VALUES (%s, %s, %s, %s, %s)",
                (servizio.nome, servizio.descrizione, servizio.durata_minuti, servizio.prezzo_centesimi, servizio.attivo)
            )
            return cur.lastrowid

    def leggi_per_id(self, servizio_id: int) -> Servizio | None:
        """
        Legge un servizio dal suo id.
        Args: servizio_id.
        Returns: il Servizio, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE id = %s", (servizio_id,))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def leggi_per_nome(self, nome: str) -> Servizio | None:
        """
        Legge un servizio dal suo nome, senza distinguere maiuscole e minuscole.
        Args: nome.
        Returns: il Servizio, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE nome = %s", (nome,))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def elenca(self, solo_attivi: bool = True) -> list[Servizio]:
        """
        Elenca i servizi in ordine di nome.
        Args: solo_attivi, se True esclude i servizi disattivati.
        Returns: la lista dei Servizi, vuota se non ce ne sono.
        """
        if solo_attivi:
            sql = _SELECT + "WHERE attivo = TRUE ORDER BY nome"
        else:
            sql = _SELECT + "ORDER BY nome"
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(sql)
            righe = cur.fetchall()
        return [_da_riga(riga) for riga in righe]

    def aggiorna(self, servizio: Servizio) -> None:
        """
        Salva tutti i campi di un servizio esistente, senza fare commit.
        Args: servizio con id.
        Raises: mysql.connector.IntegrityError se il nuovo nome è già usato.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE servizi SET nome = %s, descrizione = %s, durata_minuti = %s, "
                "prezzo_centesimi = %s, attivo = %s WHERE id = %s",
                (servizio.nome, servizio.descrizione, servizio.durata_minuti,
                 servizio.prezzo_centesimi, servizio.attivo, servizio.id),
            )
from app.modelli.servizio import Servizio

_SELECT = "SELECT id, salone_id, nome, descrizione, durata_minuti, prezzo_centesimi, attivo FROM servizi "


def _da_riga(riga: dict) -> Servizio:
    """
    Trasforma una riga di servizi in un oggetto Servizio, convertendo attivo da 0/1 a bool.
    """
    riga["attivo"] = bool(riga["attivo"])
    return Servizio(**riga)


class ServizioRepository:
    """
    Accesso alla tabella servizi. Ogni lettura è limitata a un salone: il servizio di un altro salone
    risulta inesistente.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, servizio: Servizio) -> int:
        """
        Inserisce un nuovo servizio, senza fare commit.
        Args: servizio senza id, con il salone_id.
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se il salone ha già un servizio con quel nome.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO servizi (salone_id, nome, descrizione, durata_minuti, prezzo_centesimi, attivo) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (servizio.salone_id, servizio.nome, servizio.descrizione, servizio.durata_minuti,
                 servizio.prezzo_centesimi, servizio.attivo),
            )
            return cur.lastrowid

    def leggi_per_id(self, salone_id: int, servizio_id: int) -> Servizio | None:
        """
        Legge un servizio del salone dal suo id (controllo del salone dentro la query).
        Returns: il Servizio, oppure None se non esiste o è di un altro salone.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE id = %s AND salone_id = %s", (servizio_id, salone_id))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def leggi_per_nome(self, salone_id: int, nome: str) -> Servizio | None:
        """
        Legge un servizio del salone dal suo nome, senza distinguere maiuscole e minuscole.
        Returns: il Servizio, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE salone_id = %s AND nome = %s", (salone_id, nome))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def elenca(self, salone_id: int, solo_attivi: bool = True) -> list[Servizio]:
        """
        Elenca i servizi del salone in ordine di nome.
        Args: solo_attivi, se True esclude i servizi disattivati.
        Returns: la lista dei Servizi, vuota se non ce ne sono.
        """
        sql = _SELECT + "WHERE salone_id = %s "
        if solo_attivi:
            sql += "AND attivo = TRUE "
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(sql + "ORDER BY nome", (salone_id,))
            righe = cur.fetchall()
        return [_da_riga(riga) for riga in righe]

    def aggiorna(self, servizio: Servizio) -> None:
        """
        Salva tutti i campi di un servizio esistente, senza fare commit. Il salone non cambia mai
        e fa parte della condizione: un servizio di un altro salone non viene toccato.
        Args: servizio con id e salone_id.
        Raises: mysql.connector.IntegrityError se il nuovo nome è già usato nel salone.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE servizi SET nome = %s, descrizione = %s, durata_minuti = %s, "
                "prezzo_centesimi = %s, attivo = %s WHERE id = %s AND salone_id = %s",
                (servizio.nome, servizio.descrizione, servizio.durata_minuti,
                 servizio.prezzo_centesimi, servizio.attivo, servizio.id, servizio.salone_id),
            )

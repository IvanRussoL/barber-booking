from app.modelli.utente import Utente

_SELECT = (
    "SELECT id, email, password_hash, nome, cognome, telefono, ruolo, salone_id, "
    "riceve_prenotazioni, attivo, creato_il FROM utenti "
)


def _da_riga(riga: dict) -> Utente:
    """
    Trasforma una riga di utenti in un oggetto Utente, convertendo i campi 0/1 in bool.
    """
    riga["riceve_prenotazioni"] = bool(riga["riceve_prenotazioni"])
    riga["attivo"] = bool(riga["attivo"])
    return Utente(**riga)


class UtenteRepository:
    """
    Accesso alla tabella utenti.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, utente: Utente) -> int:
        """
        Inserisce un nuovo utente, senza fare commit.
        Args: utente senza id, con la password già trasformata in hash.
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se l'email esiste già, o se il salone non è coerente
            con il ruolo (vincolo chk_utenti_salone).
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO utenti (email, password_hash, nome, cognome, telefono, ruolo, salone_id, "
                "riceve_prenotazioni, attivo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (utente.email, utente.password_hash, utente.nome, utente.cognome, utente.telefono,
                 utente.ruolo, utente.salone_id, utente.riceve_prenotazioni, utente.attivo),
            )
            return cur.lastrowid

    def leggi_per_id(self, utente_id: int) -> Utente | None:
        """
        Legge un utente dal suo id.
        Args: utente_id.
        Returns: l'Utente, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE id = %s", (utente_id,))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def leggi_per_email(self, email: str) -> Utente | None:
        """
        Legge un utente dalla sua email, senza distinguere maiuscole e minuscole.
        Args: email.
        Returns: l'Utente, oppure None se non esiste.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE email = %s", (email,))
            riga = cur.fetchone()
        return _da_riga(riga) if riga else None

    def elenca_professionisti(self, salone_id: int) -> list[Utente]:
        """
        Elenca le persone prenotabili di un salone: attive e con riceve_prenotazioni, in ordine di nome.
        Returns: la lista degli Utenti, vuota se non ce ne sono.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                _SELECT + "WHERE salone_id = %s AND attivo = TRUE AND riceve_prenotazioni = TRUE "
                "ORDER BY nome, cognome",
                (salone_id,),
            )
            righe = cur.fetchall()
        return [_da_riga(riga) for riga in righe]

    def blocca(self, utente_id: int) -> None:
        """
        Blocca la riga dell'utente con SELECT ... FOR UPDATE fino al commit o al rollback.
        Usato sul dipendente durante una prenotazione: le richieste per lo stesso dipendente
        aspettano il loro turno, quelle per altri dipendenti proseguono.
        """
        with self._conn.cursor() as cur:
            cur.execute("SELECT id FROM utenti WHERE id = %s FOR UPDATE", (utente_id,))
            cur.fetchall()


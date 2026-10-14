from app.modelli.recensione import Recensione


class RecensioneRepository:
    """
    Accesso alla tabella recensioni.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, recensione: Recensione) -> int:
        """
        Inserisce una recensione, senza fare commit.
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se l'appuntamento ha già una recensione.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO recensioni (prenotazione_id, salone_id, cliente_id, voto, commento, creato_il) "
                "VALUES (%s, %s, %s, %s, %s, COALESCE(%s, UTC_TIMESTAMP()))",
                (recensione.prenotazione_id, recensione.salone_id, recensione.cliente_id, recensione.voto,
                 recensione.commento, recensione.creato_il),
            )
            return cur.lastrowid

    def prenotazioni_recensite(self, cliente_id: int) -> set[int]:
        """
        Gli id delle prenotazioni del cliente che hanno già una recensione.
        """
        with self._conn.cursor() as cur:
            cur.execute("SELECT prenotazione_id FROM recensioni WHERE cliente_id = %s", (cliente_id,))
            return {riga[0] for riga in cur.fetchall()}

    def elenca_per_salone(self, salone_id: int, limite: int = 10) -> list[Recensione]:
        """
        Le recensioni più recenti di un salone, con l'autore mostrato come nome e iniziale del cognome.
        Returns: la lista delle Recensioni, dalla più recente.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT r.id, r.prenotazione_id, r.salone_id, r.cliente_id, r.voto, r.commento, r.creato_il, "
                "CONCAT(u.nome, ' ', LEFT(u.cognome, 1), '.') AS autore "
                "FROM recensioni r JOIN utenti u ON u.id = r.cliente_id "
                "WHERE r.salone_id = %s ORDER BY r.creato_il DESC, r.id DESC LIMIT %s",
                (salone_id, limite),
            )
            return [Recensione(**riga) for riga in cur.fetchall()]

    def media(self, salone_id: int) -> tuple[float | None, int]:
        """
        Media dei voti e numero di recensioni di un salone.
        Returns: (media arrotondata a un decimale, oppure None se non ci sono recensioni; numero).
        """
        with self._conn.cursor() as cur:
            cur.execute("SELECT AVG(voto), COUNT(*) FROM recensioni WHERE salone_id = %s", (salone_id,))
            media, numero = cur.fetchone()
        return (None if media is None else round(float(media), 1)), int(numero)

from app.modelli.pagamento import Pagamento

_SELECT = (
    "SELECT id, prenotazione_id, ordine_id, tipo, importo_centesimi, stato, "
    "riferimento_provider, creato_il FROM pagamenti "
)


class PagamentoRepository:
    """
    Accesso alla tabella pagamenti: un movimento di denaro per riga.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def inserisci(self, pagamento: Pagamento) -> int:
        """
        Inserisce un movimento, senza fare commit.
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se riferimento_provider è già presente.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pagamenti (prenotazione_id, ordine_id, tipo, importo_centesimi, stato, "
                "riferimento_provider) VALUES (%s, %s, %s, %s, %s, %s)",
                (pagamento.prenotazione_id, pagamento.ordine_id, pagamento.tipo,
                 pagamento.importo_centesimi, pagamento.stato, pagamento.riferimento_provider),
            )
            return cur.lastrowid

    def leggi_per_riferimento(self, riferimento: str, per_aggiornamento: bool = False) -> Pagamento | None:
        """
        Legge un movimento dal riferimento del provider.
        Args: per_aggiornamento, True per bloccare la riga (FOR UPDATE) finché la transazione non finisce.
        Returns: il Pagamento, oppure None se non esiste.
        """
        sql = _SELECT + "WHERE riferimento_provider = %s"
        if per_aggiornamento:
            sql += " FOR UPDATE"
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(sql, (riferimento,))
            riga = cur.fetchone()
        return Pagamento(**riga) if riga else None

    def aggiorna_stato(self, pagamento_id: int, stato: str) -> None:
        """
        Cambia lo stato di un movimento ('in_attesa', 'completato', 'fallito'), senza fare commit.
        """
        with self._conn.cursor() as cur:
            cur.execute("UPDATE pagamenti SET stato = %s WHERE id = %s", (stato, pagamento_id))

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
        Inserisce un movimento, senza fare commit. Se creato_il è vuoto vale l'ora attuale in UTC
        (lo indica solo seed.py, per creare uno storico con date passate).
        Returns: l'id assegnato da MySQL.
        Raises: mysql.connector.IntegrityError se riferimento_provider è già presente.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pagamenti (prenotazione_id, ordine_id, tipo, importo_centesimi, stato, "
                "riferimento_provider, creato_il) VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, UTC_TIMESTAMP()))",
                (pagamento.prenotazione_id, pagamento.ordine_id, pagamento.tipo,
                 pagamento.importo_centesimi, pagamento.stato, pagamento.riferimento_provider,
                 pagamento.creato_il),
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

    def online_completati(self, prenotazione_id: int) -> list[Pagamento]:
        """
        Pagamenti online riusciti di una prenotazione, da rimborsare in caso di annullamento.
        Returns: la lista dei Pagamenti.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                _SELECT + "WHERE prenotazione_id = %s AND tipo = 'online' AND stato = 'completato'",
                (prenotazione_id,),
            )
            return [Pagamento(**riga) for riga in cur.fetchall()]

    def online_della_prenotazione(self, prenotazione_id: int) -> list[Pagamento]:
        """
        Pagamenti online di una prenotazione, in qualsiasi stato, dal più recente.
        Returns: la lista dei Pagamenti.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT + "WHERE prenotazione_id = %s AND tipo = 'online' ORDER BY id DESC", (prenotazione_id,))
            return [Pagamento(**riga) for riga in cur.fetchall()]

    def totale_pagato(self, prenotazione_id: int) -> int:
        """
        Quanto ha pagato il cliente per una prenotazione: movimenti completati, rimborsi sottratti.
        Returns: l'importo netto in centesimi (0 se non ci sono movimenti).
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(CASE WHEN tipo = 'rimborso' THEN -importo_centesimi "
                "ELSE importo_centesimi END), 0) FROM pagamenti "
                "WHERE prenotazione_id = %s AND stato = 'completato'",
                (prenotazione_id,),
            )
            return int(cur.fetchone()[0])


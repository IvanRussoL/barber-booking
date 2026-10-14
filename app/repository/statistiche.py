from datetime import datetime


class StatisticheRepository:
    """
    Letture per le statistiche: righe semplici, che il servizio trasforma in tabelle pandas.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def prenotazioni_confermate(self, salone_id: int, da: datetime, a: datetime,
                                dipendente_id: int | None = None) -> list[dict]:
        """
        Prenotazioni confermate del salone con inizio in [da, a), con professionista e valore dei servizi.
        Args: date e ore in UTC; dipendente_id per limitarsi a un professionista.
        Returns: righe con id, dipendente_id, professionista, cliente_id, inizio, totale_centesimi.
        """
        sql = (
            "SELECT p.id, p.dipendente_id, CONCAT(u.nome, ' ', u.cognome) AS professionista, "
            "p.cliente_id, p.inizio, SUM(ps.prezzo_centesimi) AS totale_centesimi "
            "FROM prenotazioni p "
            "JOIN utenti u ON u.id = p.dipendente_id "
            "JOIN prenotazioni_servizi ps ON ps.prenotazione_id = p.id "
            "WHERE p.salone_id = %s AND p.stato = 'confermata' AND p.inizio >= %s AND p.inizio < %s "
        )
        parametri = [salone_id, da, a]
        if dipendente_id is not None:
            sql += "AND p.dipendente_id = %s "
            parametri.append(dipendente_id)
        sql += "GROUP BY p.id, p.dipendente_id, u.nome, u.cognome, p.cliente_id, p.inizio"
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(sql, parametri)
            return cur.fetchall()

    def movimenti_completati(self, salone_id: int, da: datetime, a: datetime) -> list[dict]:
        """
        Movimenti di denaro completati del salone registrati in [da, a): pagamenti online, saldi in sede
        e rimborsi. Il salone si ricava dalla prenotazione o dall'ordine del movimento.
        Args: date e ore in UTC.
        Returns: righe con tipo, importo_centesimi, creato_il.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT pg.tipo, pg.importo_centesimi, pg.creato_il FROM pagamenti pg "
                "LEFT JOIN prenotazioni p ON p.id = pg.prenotazione_id "
                "LEFT JOIN ordini o ON o.id = pg.ordine_id "
                "WHERE pg.stato = 'completato' AND pg.creato_il >= %s AND pg.creato_il < %s "
                "AND (p.salone_id = %s OR o.salone_id = %s)",
                (da, a, salone_id, salone_id),
            )
            return cur.fetchall()

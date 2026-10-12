from app.modelli.impostazioni import Impostazioni


class ImpostazioniRepository:
    """
    Accesso alla tabella impostazioni, che contiene una sola riga.
    """

    def __init__(self, connessione):
        self._conn = connessione

    def leggi(self) -> Impostazioni:
        """
        Legge le impostazioni del salone.
        Returns: l'oggetto Impostazioni con i valori della riga.
        """
        with self._conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id, nome_salone, indirizzo, telefono, fuso_orario, latitudine, "
                "longitudine, percentuale_acconto, mesi_prenotabili "
                "FROM impostazioni WHERE id = 1"
            )
            riga = cur.fetchone()
        return Impostazioni(**riga)
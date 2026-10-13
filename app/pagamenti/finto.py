import secrets

from app.pagamenti.provider import PaymentProvider, SessionePagamento


class FakeProvider(PaymentProvider):
    """
    Provider simulato, senza servizi esterni: la "pagina di pagamento" è una pagina del sito
    con i pulsanti Paga e Annulla. Tiene in memoria le operazioni per poterle controllare nei test.
    """

    def __init__(self, url_pagamento: str = "/cliente/pagamento/{riferimento}"):
        self._url_pagamento = url_pagamento
        self.sessioni_chiuse: list[str] = []
        self.rimborsi: list[tuple[str, int]] = []

    def crea_sessione(self, importo_centesimi: int, descrizione: str) -> SessionePagamento:
        """
        Crea un riferimento casuale e la pagina simulata in cui pagare.
        Returns: la SessionePagamento.
        """
        riferimento = "finto_" + secrets.token_hex(12)
        return SessionePagamento(riferimento, self._url_pagamento.format(riferimento=riferimento))

    def chiudi_sessione(self, riferimento: str) -> None:
        """
        Registra la chiusura della sessione.
        """
        self.sessioni_chiuse.append(riferimento)

    def rimborsa(self, riferimento: str, importo_centesimi: int) -> str:
        """
        Registra il rimborso.
        Returns: un riferimento casuale del rimborso.
        """
        self.rimborsi.append((riferimento, importo_centesimi))
        return "finto_rimborso_" + secrets.token_hex(12)

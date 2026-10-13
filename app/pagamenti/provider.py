from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SessionePagamento:
    """
    Pagamento aperto presso il provider: riferimento univoco e pagina in cui il cliente paga.
    """
    riferimento: str
    url: str


class PaymentProvider(ABC):
    """
    Operazioni comuni a tutti i provider di pagamento. I servizi usano solo questa interfaccia,
    quindi FakeProvider (test e demo) e un futuro StripeProvider sono intercambiabili.
    """

    @abstractmethod
    def crea_sessione(self, importo_centesimi: int, descrizione: str) -> SessionePagamento:
        """
        Apre un pagamento dell'importo indicato.
        Returns: la SessionePagamento con riferimento e pagina di pagamento.
        """

    @abstractmethod
    def chiudi_sessione(self, riferimento: str) -> None:
        """
        Chiude un pagamento non ancora eseguito, così non può più essere pagato.
        """

    @abstractmethod
    def rimborsa(self, riferimento: str, importo_centesimi: int) -> str:
        """
        Restituisce al cliente l'importo di un pagamento eseguito.
        Returns: il riferimento del rimborso presso il provider.
        """

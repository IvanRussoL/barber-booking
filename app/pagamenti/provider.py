from abc import ABC, abstractmethod
from dataclasses import dataclass

# Importo minimo di un pagamento online: Stripe non accetta addebiti sotto 0,50 € (documentazione "Supported currencies").
IMPORTO_MINIMO_CENTESIMI = 50


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
    quindi FakeProvider (test e demo) e StripeProvider sono intercambiabili.
    """

    @abstractmethod
    def crea_sessione(self, importo_centesimi: int, descrizione: str, prenotazione_id: int) -> SessionePagamento:
        """
        Apre un pagamento dell'importo indicato per una prenotazione (l'id serve alle pagine di ritorno).
        Returns: la SessionePagamento con riferimento e pagina di pagamento.
        Raises: PagamentoNonDisponibileError se il provider non risponde o rifiuta.
        """

    @abstractmethod
    def chiudi_sessione(self, riferimento: str) -> None:
        """
        Chiude un pagamento non ancora eseguito, così non può più essere pagato.
        Se è già chiuso o scaduto non fa niente.
        """

    @abstractmethod
    def rimborsa(self, riferimento: str, importo_centesimi: int) -> str:
        """
        Restituisce al cliente l'importo di un pagamento eseguito.
        Returns: il riferimento del rimborso presso il provider.
        Raises: PagamentoNonDisponibileError se il provider non risponde o rifiuta.
        """

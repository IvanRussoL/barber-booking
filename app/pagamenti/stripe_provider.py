import time

import stripe

from app.eccezioni import PagamentoNonDisponibileError
from app.pagamenti.provider import PaymentProvider, SessionePagamento

# La sessione di Stripe Checkout deve durare almeno 30 minuti (documentazione di Stripe). Un minuto in più
# rispetto al blocco dello slot: se il cliente paga tra il 30° e il 31° minuto, il pagamento arriva dopo
# la scadenza della prenotazione e viene rimborsato da conferma_pagamento, come qualsiasi pagamento tardivo.
SECONDI_DI_VALIDITA = 31 * 60


class StripeProvider(PaymentProvider):
    """
    Pagamenti con Stripe Checkout in modalità test: il cliente paga sulla pagina di Stripe con carta,
    Google Pay o PayPal (i metodi si attivano dal Dashboard di Stripe, non dal codice).
    La conferma arriva dal webhook (rotta /webhook/stripe), mai dalla pagina a cui torna il cliente.
    """

    def __init__(self, chiave_segreta: str, segreto_webhook: str, url_sito: str):
        """
        Args: chiave_segreta (sk_test_...), segreto_webhook (whsec_...), url_sito (es. http://127.0.0.1:5000),
            usato per le pagine a cui Stripe riporta il cliente.
        """
        self._client = stripe.StripeClient(chiave_segreta)
        self._segreto_webhook = segreto_webhook
        self._url_sito = url_sito.rstrip("/")

    def crea_sessione(self, importo_centesimi: int, descrizione: str, prenotazione_id: int) -> SessionePagamento:
        """
        Crea una sessione di Checkout per un importo in euro, con scadenza a 31 minuti.
        Returns: la SessionePagamento con l'id della sessione (cs_...) e la pagina di Stripe.
        Raises: PagamentoNonDisponibileError se Stripe rifiuta o non risponde.
        """
        ritorno = f"{self._url_sito}/cliente/prenotazioni/{prenotazione_id}/pagamento"
        try:
            sessione = self._client.v1.checkout.sessions.create(params={
                "mode": "payment",
                "line_items": [{
                    "quantity": 1,
                    "price_data": {"currency": "eur", "unit_amount": importo_centesimi,
                                   "product_data": {"name": descrizione}},
                }],
                "success_url": ritorno + "-eseguito",
                "cancel_url": ritorno + "-annullato",
                "expires_at": int(time.time()) + SECONDI_DI_VALIDITA,
                "client_reference_id": str(prenotazione_id),
                "locale": "it",
                "submit_type": "book",
            })
        except stripe.StripeError as errore:
            raise PagamentoNonDisponibileError("Il pagamento non è disponibile in questo momento: riprova tra poco.") from errore
        return SessionePagamento(sessione.id, sessione.url)

    def chiudi_sessione(self, riferimento: str) -> None:
        """
        Fa scadere subito la sessione, così non può più essere pagata. Stripe risponde con un errore
        se è già scaduta o completata: in quel caso non c'è niente da chiudere.
        """
        try:
            self._client.v1.checkout.sessions.expire(riferimento)
        except stripe.InvalidRequestError:
            pass

    def rimborsa(self, riferimento: str, importo_centesimi: int) -> str:
        """
        Rimborsa il pagamento di una sessione: il rimborso si fa sul PaymentIntent della sessione.
        La chiave di idempotenza fa sì che una richiesta ripetuta non produca un secondo rimborso.
        Returns: l'id del rimborso (re_...).
        Raises: PagamentoNonDisponibileError se Stripe rifiuta o non risponde.
        """
        try:
            sessione = self._client.v1.checkout.sessions.retrieve(riferimento)
            rimborso = self._client.v1.refunds.create(
                params={"payment_intent": sessione.payment_intent, "amount": importo_centesimi},
                options={"idempotency_key": f"rimborso-{riferimento}"},
            )
        except stripe.StripeError as errore:
            raise PagamentoNonDisponibileError("Il rimborso non è riuscito: riprova tra poco.") from errore
        return rimborso.id

    def leggi_evento(self, corpo: bytes, firma: str | None) -> tuple[str, str, str]:
        """
        Verifica la firma di una notifica del webhook e ne estrae i dati che servono.
        Args: corpo, la richiesta così come arriva (la firma vale solo sui byte originali);
            firma, l'intestazione Stripe-Signature.
        Returns: (tipo dell'evento, id della sessione, stato del pagamento della sessione).
        Raises: ValueError se il corpo non è valido; stripe.SignatureVerificationError se la firma non torna.
        """
        evento = self._client.construct_event(corpo, firma, self._segreto_webhook)
        sessione = evento.data.object.to_dict()  # dizionario normale: i campi assenti non danno errore
        return evento.type, sessione.get("id", ""), sessione.get("payment_status", "")

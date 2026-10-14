import stripe
from flask import Blueprint, abort, current_app, request

from app.db import ottieni_connessione
from app.eccezioni import RisorsaNonTrovataError
from app.pagamenti.stripe_provider import StripeProvider
from app.servizi.prenotazione import PrenotazioneService

bp = Blueprint("webhook", __name__, url_prefix="/webhook")

# Eventi che confermano un pagamento: la sessione completata e pagata, oppure un pagamento "ritardato"
# che va a buon fine dopo (Stripe li invia per alcuni metodi di pagamento).
EVENTO_COMPLETATO = "checkout.session.completed"
EVENTO_PAGAMENTO_RITARDATO = "checkout.session.async_payment_succeeded"


@bp.route("/stripe", methods=["POST"])
def stripe_webhook():
    """
    Notifiche di Stripe. È pubblica (la chiama Stripe, non un utente) ed esente dal CSRF: la protezione
    è la firma, verificata con il segreto del webhook prima di leggere qualsiasi dato.
    La conferma è idempotente (riferimento_provider univoco e già "completato"): se Stripe ripete
    la stessa notifica non succede niente. Risponde 200 anche agli eventi che non interessano,
    così Stripe non li ripete.
    """
    provider = current_app.extensions["provider_pagamenti"]
    if not isinstance(provider, StripeProvider):
        abort(404)
    try:
        tipo, riferimento, stato = provider.leggi_evento(request.get_data(), request.headers.get("Stripe-Signature"))
    except (ValueError, stripe.SignatureVerificationError):
        return "Firma non valida", 400
    if (tipo == EVENTO_COMPLETATO and stato == "paid") or tipo == EVENTO_PAGAMENTO_RITARDATO:
        try:
            PrenotazioneService(ottieni_connessione(), provider).conferma_pagamento(riferimento)
        except RisorsaNonTrovataError:
            pass  # sessione che non è di una nostra prenotazione: niente da fare
    return "", 200

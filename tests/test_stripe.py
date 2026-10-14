"""
StripeProvider e webhook, senza chiamare Stripe: le funzioni della libreria sono sostituite da finte
e le firme dei webhook sono calcolate come le calcola Stripe (HMAC-SHA256 di "timestamp.corpo").
"""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
import stripe

from app import create_app
from app.eccezioni import DatiNonValidiError, PagamentoNonDisponibileError
from app.pagamenti.stripe_provider import SECONDI_DI_VALIDITA, StripeProvider
from app.servizi.prenotazione import PrenotazioneService, calcola_acconto
from app.servizi.salone import SaloneService

SEGRETO = "whsec_prova"


@pytest.fixture
def provider():
    return StripeProvider("sk_test_finta", SEGRETO, "http://127.0.0.1:5000/")


def _firma(corpo: bytes, segreto: str = SEGRETO) -> str:
    istante = int(time.time())
    impronta = hmac.new(segreto.encode(), f"{istante}.".encode() + corpo, hashlib.sha256).hexdigest()
    return f"t={istante},v1={impronta}"


def _evento(tipo: str, sessione: str = "cs_test_1", stato: str = "paid") -> bytes:
    return json.dumps({"id": "evt_1", "object": "event", "type": tipo,
                       "data": {"object": {"id": sessione, "object": "checkout.session", "payment_status": stato}}}).encode()


# --- Importi ---

@pytest.mark.parametrize("totale, percentuale, acconto", [(1000, 1, 50), (3550, 30, 1065), (30, 50, 30)])
def test_acconto_mai_sotto_l_importo_minimo(totale, percentuale, acconto):
    assert calcola_acconto(totale, percentuale) == acconto


def test_prezzo_minimo_dei_servizi(conn, salone_test):
    with pytest.raises(DatiNonValidiError, match="0,50"):
        SaloneService(conn, salone_test).crea_servizio("Prova prezzo", "", "30", "0,49")


# --- StripeProvider ---

def test_crea_sessione(provider, monkeypatch):
    ricevuti = {}

    def crea(params, options=None):
        ricevuti.update(params)
        return SimpleNamespace(id="cs_test_1", url="https://checkout.stripe.com/c/pay/cs_test_1")

    monkeypatch.setattr(provider._client.v1.checkout.sessions, "create", crea)
    sessione = provider.crea_sessione(1065, "Salone – prenotazione n. 7", 7)
    assert (sessione.riferimento, sessione.url) == ("cs_test_1", "https://checkout.stripe.com/c/pay/cs_test_1")
    riga = ricevuti["line_items"][0]
    assert ricevuti["mode"] == "payment" and riga["quantity"] == 1
    assert riga["price_data"]["currency"] == "eur" and riga["price_data"]["unit_amount"] == 1065
    assert ricevuti["success_url"] == "http://127.0.0.1:5000/cliente/prenotazioni/7/pagamento-eseguito"
    assert ricevuti["cancel_url"] == "http://127.0.0.1:5000/cliente/prenotazioni/7/pagamento-annullato"
    assert abs(ricevuti["expires_at"] - (time.time() + SECONDI_DI_VALIDITA)) < 5
    assert SECONDI_DI_VALIDITA >= 30 * 60  # minimo richiesto da Stripe


def test_errore_di_stripe_diventa_pagamento_non_disponibile(provider, monkeypatch):
    def rifiuta(*args, **kwargs):
        raise stripe.APIConnectionError("rete assente")

    monkeypatch.setattr(provider._client.v1.checkout.sessions, "create", rifiuta)
    with pytest.raises(PagamentoNonDisponibileError):
        provider.crea_sessione(1065, "Prova", 7)


def test_chiudi_sessione_gia_scaduta(provider, monkeypatch):
    def gia_scaduta(riferimento, *args, **kwargs):
        raise stripe.InvalidRequestError("Session already expired", "session")

    monkeypatch.setattr(provider._client.v1.checkout.sessions, "expire", gia_scaduta)
    provider.chiudi_sessione("cs_test_1")  # nessun errore: non c'è niente da chiudere


def test_rimborso_sul_payment_intent(provider, monkeypatch):
    chiamate = []
    monkeypatch.setattr(provider._client.v1.checkout.sessions, "retrieve",
                        lambda riferimento, *a, **k: SimpleNamespace(payment_intent="pi_test_1"))

    def rimborsa(params, options=None):
        chiamate.append((params, options))
        return SimpleNamespace(id="re_test_1")

    monkeypatch.setattr(provider._client.v1.refunds, "create", rimborsa)
    assert provider.rimborsa("cs_test_1", 1065) == "re_test_1"
    assert chiamate == [({"payment_intent": "pi_test_1", "amount": 1065}, {"idempotency_key": "rimborso-cs_test_1"})]


def test_firma_del_webhook(provider):
    corpo = _evento("checkout.session.completed")
    assert provider.leggi_evento(corpo, _firma(corpo)) == ("checkout.session.completed", "cs_test_1", "paid")
    with pytest.raises(stripe.SignatureVerificationError):
        provider.leggi_evento(corpo, _firma(corpo, "whsec_sbagliato"))
    with pytest.raises(stripe.SignatureVerificationError):
        provider.leggi_evento(corpo + b" ", _firma(corpo))  # corpo modificato dopo la firma


# --- Rotta del webhook ---

@pytest.fixture
def client_stripe(provider):
    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False, "PROVIDER_PAGAMENTI": provider})
    return app.test_client()  # CSRF attivo: il webhook deve funzionare lo stesso


@pytest.fixture
def conferme(monkeypatch):
    riferimenti = []
    monkeypatch.setattr(PrenotazioneService, "conferma_pagamento",
                        lambda self, riferimento, adesso=None: riferimenti.append(riferimento) or True)
    return riferimenti


def _invia(client, corpo, firma):
    return client.post("/webhook/stripe", data=corpo, headers={"Stripe-Signature": firma},
                       content_type="application/json")


def test_webhook_conferma_solo_pagamenti_riusciti(client_stripe, conferme):
    for tipo, stato in [("checkout.session.completed", "paid"), ("checkout.session.async_payment_succeeded", "paid"),
                        ("checkout.session.completed", "unpaid"), ("checkout.session.expired", "unpaid"),
                        ("customer.created", "")]:
        corpo = _evento(tipo, "cs_" + tipo + stato, stato)
        assert _invia(client_stripe, corpo, _firma(corpo)).status_code == 200
    assert conferme == ["cs_checkout.session.completedpaid", "cs_checkout.session.async_payment_succeededpaid"]


def test_webhook_rifiuta_firme_non_valide(client_stripe, conferme):
    corpo = _evento("checkout.session.completed")
    assert _invia(client_stripe, corpo, _firma(corpo, "whsec_sbagliato")).status_code == 400
    assert _invia(client_stripe, corpo, "").status_code == 400
    assert conferme == []


def test_webhook_sessione_sconosciuta(client_stripe):
    corpo = _evento("checkout.session.completed", "cs_test_che_non_esiste")
    assert _invia(client_stripe, corpo, _firma(corpo)).status_code == 200


def test_webhook_assente_con_il_pagamento_simulato(client):
    assert client.post("/webhook/stripe", data=b"{}").status_code == 404


def test_con_stripe_il_pagamento_simulato_non_esiste(client_stripe, utenti_accessi):
    with client_stripe.session_transaction() as sessione:
        sessione["utente_id"] = utenti_accessi["cliente"]
    assert client_stripe.get("/cliente/pagamento/cs_test_1").status_code == 404
    # Il POST "Paga" senza token CSRF è già bloccato (400); anche con il token il provider non è quello simulato.
    assert client_stripe.post("/cliente/pagamento/cs_test_1/paga").status_code in (400, 404)


def test_pagine_di_ritorno_solo_per_le_proprie_prenotazioni(client, utenti_accessi):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utenti_accessi["cliente"]
    assert client.get("/cliente/prenotazioni/999999/pagamento-eseguito").status_code == 404
    assert client.get("/cliente/prenotazioni/999999/pagamento-annullato").status_code == 404

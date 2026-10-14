"""
Cambio della password e limite ai tentativi sbagliati di login.
"""
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.eccezioni import CredenzialiNonValideError, DatiNonValidiError
from app.modelli.utente import Utente
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService


@pytest.fixture
def utente_id(conn):
    return UtenteRepository(conn).inserisci(Utente(
        "password@account.test", generate_password_hash("vecchia-123"), "Paola", "Password", "3330000020",
    ))


def test_cambio_password(conn, utente_id):
    auth = AuthService(conn)
    auth.cambia_password(utente_id, "vecchia-123", "nuova-4567", "nuova-4567")
    assert auth.autentica("password@account.test", "nuova-4567").id == utente_id
    with pytest.raises(CredenzialiNonValideError):
        auth.autentica("password@account.test", "vecchia-123")


@pytest.mark.parametrize("attuale, nuova, conferma", [
    ("sbagliata", "nuova-4567", "nuova-4567"),    # password attuale errata
    ("vecchia-123", "corta", "corta"),             # meno di 8 caratteri
    ("vecchia-123", "nuova-4567", "nuova-4568"),  # le due nuove non coincidono
    ("vecchia-123", "vecchia-123", "vecchia-123"),  # uguale a quella attuale
])
def test_cambio_password_rifiutato(conn, utente_id, attuale, nuova, conferma):
    with pytest.raises(DatiNonValidiError):
        AuthService(conn).cambia_password(utente_id, attuale, nuova, conferma)


def test_pagina_account(client, utenti_accessi):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utenti_accessi["cliente"]
    assert "Cambia la password" in client.get("/account/").text
    risposta = client.post("/account/", data={"attuale": "sbagliata", "nuova": "nuova-4567", "conferma": "nuova-4567"})
    assert risposta.status_code == 400 and "non è corretta" in risposta.text


def test_limite_ai_tentativi_di_login():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": True})
    client = app.test_client()
    sbagliato = {"email": "nessuno@account.test", "password": "sbagliata"}
    da_un_ip = {"REMOTE_ADDR": "10.0.0.1"}
    for _ in range(5):
        assert client.post("/auth/login", data=sbagliato, environ_base=da_un_ip).status_code == 400
    bloccato = client.post("/auth/login", data=sbagliato, environ_base=da_un_ip)
    assert bloccato.status_code == 429 and "Troppi tentativi" in bloccato.text
    assert client.get("/auth/login", environ_base=da_un_ip).status_code == 200  # la pagina si apre ancora
    # Un altro indirizzo non è bloccato.
    assert client.post("/auth/login", data=sbagliato, environ_base={"REMOTE_ADDR": "10.0.0.2"}).status_code == 400

import re

import pytest

from app import create_app

# Aree aperte a tutti: "static" è la rotta dei file statici creata da Flask.
AREE_PUBBLICHE = {"pubblico", "auth", "static"}

# Per ogni area riservata, i ruoli che possono entrare.
# Il proprietario di prova riceve prenotazioni, quindi entra anche nell'area dipendente.
RUOLI_AMMESSI = {
    "account": {"cliente", "dipendente", "proprietario"},
    "cliente": {"cliente"},
    "dipendente": {"dipendente", "proprietario"},
    "proprietario": {"proprietario"},
}


def _rotte_riservate() -> list[tuple[str, str, str]]:
    """
    Legge dall'app tutte le rotte delle aree riservate.
    Returns: lista di (area, url con 1 al posto dei parametri, metodo HTTP).
    """
    rotte = []
    for regola in create_app().url_map.iter_rules():
        area = regola.endpoint.split(".")[0]
        if area in RUOLI_AMMESSI:
            metodo = "GET" if "GET" in regola.methods else "POST"
            rotte.append((area, re.sub(r"<[^>]+>", "1", regola.rule), metodo))
    return rotte


ROTTE_RISERVATE = _rotte_riservate()


def test_ogni_rotta_appartiene_a_un_area_conosciuta(app):
    for regola in app.url_map.iter_rules():
        area = regola.endpoint.split(".")[0]
        assert area in AREE_PUBBLICHE or area in RUOLI_AMMESSI, f"Area non classificata: {regola.rule}"


@pytest.mark.parametrize("area, url, metodo", ROTTE_RISERVATE)
def test_anonimo_mandato_al_login(client, area, url, metodo):
    risposta = client.open(url, method=metodo)
    assert risposta.status_code == 302
    assert risposta.headers["Location"].startswith("/auth/login")


@pytest.mark.parametrize("ruolo", ["cliente", "dipendente", "proprietario"])
@pytest.mark.parametrize("area, url, metodo", ROTTE_RISERVATE)
def test_accesso_per_ruolo(client, utenti_accessi, ruolo, area, url, metodo):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utenti_accessi[ruolo]

    if ruolo not in RUOLI_AMMESSI[area]:
        assert client.open(url, method=metodo).status_code == 403
    elif metodo == "GET":
        risposta = client.get(url)
        assert risposta.status_code != 403
        assert "/auth/login" not in risposta.headers.get("Location", "")
    else:
        pytest.skip("POST consentito: non lo invio per non modificare i dati")

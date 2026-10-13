from datetime import UTC, datetime, timedelta

import pytest

from app.db import crea_connessione
from app.modelli.prenotazione import Prenotazione
from app.modelli.utente import Utente
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.utente import UtenteRepository

EMAIL_ALTRO_CLIENTE = "altro@idor.test"


def _pulisci(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM prenotazioni WHERE cliente_id IN (SELECT id FROM utenti WHERE email = %s)",
                    (EMAIL_ALTRO_CLIENTE,))
        cur.execute("DELETE FROM utenti WHERE email = %s", (EMAIL_ALTRO_CLIENTE,))
    conn.commit()


@pytest.fixture
def prenotazione_altrui(utenti_accessi):
    """
    Prenotazione confermata di un altro cliente, salvata con commit reale perché la legga l'app.
    Returns: l'id della prenotazione.
    """
    conn = crea_connessione()
    _pulisci(conn)
    altro_id = UtenteRepository(conn).inserisci(Utente(EMAIL_ALTRO_CLIENTE, "x", "Altro", "Cliente", "3330000099"))
    inizio = datetime.now(UTC).replace(tzinfo=None, microsecond=0) + timedelta(days=3)
    prenotazione_id = PrenotazioneRepository(conn).inserisci(Prenotazione(
        cliente_id=altro_id, dipendente_id=utenti_accessi["dipendente"], inizio=inizio,
        fine=inizio + timedelta(minutes=30), modalita_pagamento="completo", scade_il=inizio,
        stato="confermata",
    ))
    conn.commit()
    yield prenotazione_id
    _pulisci(conn)
    conn.close()


def _accedi(client, utente_id):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utente_id


def test_cliente_non_vede_ne_annulla_prenotazioni_altrui(client, utenti_accessi, prenotazione_altrui):
    _accedi(client, utenti_accessi["cliente"])
    url = f"/cliente/prenotazioni/{prenotazione_altrui}/annulla"
    assert client.get(url).status_code == 404
    assert client.post(url).status_code == 404
    conn = crea_connessione()
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_altrui).stato == "confermata"
    conn.close()


def test_area_cliente_mostra_solo_le_proprie(client, utenti_accessi, prenotazione_altrui):
    _accedi(client, utenti_accessi["cliente"])
    pagina = client.get("/cliente/").text
    assert "Non hai ancora prenotazioni" in pagina


def test_agenda_mostra_gli_appuntamenti_del_professionista(client, utenti_accessi, prenotazione_altrui):
    _accedi(client, utenti_accessi["dipendente"])
    assert "Altro Cliente" in client.get("/dipendente/").text
    _accedi(client, utenti_accessi["proprietario"])
    assert "Altro Cliente" not in client.get("/dipendente/").text

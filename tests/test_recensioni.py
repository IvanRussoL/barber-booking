"""
Recensioni: solo per appuntamenti svolti, una per appuntamento, solo dal cliente che li ha avuti.
"""
from datetime import UTC, datetime, timedelta

import pytest

from app.db import crea_connessione
from app.eccezioni import DatiNonValidiError, RecensioneNonConsentitaError, RisorsaNonTrovataError
from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.modelli.recensione import Recensione
from app.pagamenti.finto import FakeProvider
from app.repository.pagamento import PagamentoRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.recensione import RecensioneRepository
from app.servizi.prenotazione import PrenotazioneService
from app.servizi.recensioni import RecensioniService
from app.servizi.saloni import SaloniService

INIZIO = datetime(2026, 10, 14, 8, 0)           # mercoledì 10:00 italiane
PRIMA = datetime(2026, 10, 14, 7, 0, tzinfo=UTC)   # un'ora prima dell'inizio
DOPO = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)    # 30 minuti dopo la fine


def _prenotazione(conn, salone, stato="confermata") -> int:
    prenotazione_id = PrenotazioneRepository(conn).inserisci(Prenotazione(
        salone_id=salone["salone_id"], cliente_id=salone["cliente"].id, dipendente_id=salone["dipendente_id"],
        inizio=INIZIO, fine=INIZIO + timedelta(minutes=30), modalita_pagamento="completo", scade_il=INIZIO,
        stato=stato, servizi=[ServizioPrenotato(salone["taglio_id"], "Taglio prova", 30, 2000)],
    ))
    PagamentoRepository(conn).inserisci(Pagamento(
        tipo="online", importo_centesimi=2000, prenotazione_id=prenotazione_id, stato="completato",
    ))
    return prenotazione_id


def test_recensione_dopo_l_appuntamento(conn, salone):
    prenotazione_id = _prenotazione(conn, salone)
    servizio = RecensioniService(conn)
    servizio.crea(prenotazione_id, salone["cliente"].id, "4", "  Ottimo taglio  ", DOPO)
    media, numero, elenco = servizio.del_salone(salone["salone_id"])
    assert (media, numero) == (4.0, 1)
    assert (elenco[0].voto, elenco[0].commento, elenco[0].autore) == (4, "Ottimo taglio", "Carla C.")


def test_prima_dell_appuntamento_non_si_recensisce(conn, salone):
    prenotazione_id = _prenotazione(conn, salone)
    with pytest.raises(RecensioneNonConsentitaError):
        RecensioniService(conn).crea(prenotazione_id, salone["cliente"].id, "5", "", PRIMA)


def test_una_sola_recensione_per_appuntamento(conn, salone):
    prenotazione_id = _prenotazione(conn, salone)
    servizio = RecensioniService(conn)
    servizio.crea(prenotazione_id, salone["cliente"].id, "5", "", DOPO)
    with pytest.raises(RecensioneNonConsentitaError):
        servizio.crea(prenotazione_id, salone["cliente"].id, "1", "", DOPO)


def test_appuntamento_annullato_non_si_recensisce(conn, salone):
    prenotazione_id = _prenotazione(conn, salone, stato="annullata")
    with pytest.raises(RecensioneNonConsentitaError):
        RecensioniService(conn).crea(prenotazione_id, salone["cliente"].id, "5", "", DOPO)


def test_appuntamento_di_un_altro_cliente_non_trovato(conn, salone):
    prenotazione_id = _prenotazione(conn, salone)
    with pytest.raises(RisorsaNonTrovataError):
        RecensioniService(conn).crea(prenotazione_id, salone["dipendente_id"], "5", "", DOPO)


@pytest.mark.parametrize("voto, commento", [("0", ""), ("6", ""), ("cinque", ""), ("", ""), ("4", "a" * 501)])
def test_dati_non_validi(conn, salone, voto, commento):
    prenotazione_id = _prenotazione(conn, salone)
    with pytest.raises(DatiNonValidiError):
        RecensioniService(conn).crea(prenotazione_id, salone["cliente"].id, voto, commento, DOPO)


def test_storico_indica_cosa_si_puo_recensire(conn, salone):
    prenotazione_id = _prenotazione(conn, salone)
    servizio = PrenotazioneService(conn, FakeProvider())
    assert servizio.storico_cliente(salone["cliente"].id, PRIMA)[0].recensibile is False
    assert servizio.storico_cliente(salone["cliente"].id, DOPO)[0].recensibile is True
    RecensioniService(conn).crea(prenotazione_id, salone["cliente"].id, "5", "", DOPO)
    assert servizio.storico_cliente(salone["cliente"].id, DOPO)[0].recensibile is False


def test_ricerca_ordinata_per_recensioni(conn, salone, altro_salone_test):
    recensioni = RecensioneRepository(conn)
    prenotazione_id = _prenotazione(conn, salone)
    recensioni.inserisci(Recensione(prenotazione_id, salone["salone_id"], salone["cliente"].id, 2))
    # Nell'altro salone una recensione da 5 (la prenotazione serve solo per il vincolo della chiave esterna).
    altra_id = _prenotazione(conn, salone)
    recensioni.inserisci(Recensione(altra_id, altro_salone_test, salone["cliente"].id, 5))
    per_zona = {r.salone.id: r for r in SaloniService(conn).cerca_per_zona("Campania")}
    assert per_zona[salone["salone_id"]].media_voti == 2.0
    assert per_zona[salone["salone_id"]].numero_recensioni == 1
    lazio = SaloniService(conn).cerca_per_zona("Lazio", ordine="recensioni")
    assert lazio[0].salone.id == altro_salone_test and lazio[0].media_voti == 5.0


# --- Pagine (dati salvati davvero) ---

@pytest.fixture
def appuntamento_svolto(utenti_accessi, salone_test):
    """
    Appuntamento già svolto e pagato del cliente dei test di accesso, salvato con commit e poi cancellato.
    """
    conn = crea_connessione()
    inizio = datetime.now(UTC).replace(tzinfo=None, microsecond=0) - timedelta(days=2)
    prenotazione_id = PrenotazioneRepository(conn).inserisci(Prenotazione(
        salone_id=salone_test, cliente_id=utenti_accessi["cliente"], dipendente_id=utenti_accessi["dipendente"],
        inizio=inizio, fine=inizio + timedelta(minutes=30), modalita_pagamento="completo", scade_il=inizio,
        stato="confermata",
    ))
    PagamentoRepository(conn).inserisci(Pagamento(
        tipo="online", importo_centesimi=1000, prenotazione_id=prenotazione_id, stato="completato",
    ))
    conn.commit()
    yield prenotazione_id
    with conn.cursor() as cur:
        cur.execute("DELETE FROM recensioni WHERE prenotazione_id = %s", (prenotazione_id,))
        cur.execute("DELETE FROM pagamenti WHERE prenotazione_id = %s", (prenotazione_id,))
        cur.execute("DELETE FROM prenotazioni WHERE id = %s", (prenotazione_id,))
    conn.commit()
    conn.close()


def _accedi(client, utente_id):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utente_id


def test_pagina_recensione_e_testo_mostrato_senza_html(client, utenti_accessi, salone_test, appuntamento_svolto):
    url = f"/cliente/prenotazioni/{appuntamento_svolto}/recensione"
    _accedi(client, utenti_accessi["cliente"])
    assert "Lascia una recensione" in client.get("/cliente/").text
    assert client.get(url).status_code == 200
    risposta = client.post(url, data={"voto": "5", "commento": "<script>alert(1)</script> bravi"})
    assert risposta.status_code == 302
    pagina = client.get(f"/saloni/{salone_test}").text
    assert "&lt;script&gt;alert(1)&lt;/script&gt; bravi" in pagina and "<script>alert(1)" not in pagina
    assert client.post(url, data={"voto": "1"}).status_code == 302  # seconda volta: torna all'area, niente di nuovo
    conn = crea_connessione()
    assert RecensioneRepository(conn).media(salone_test)[1] >= 1
    with conn.cursor() as cur:
        cur.execute("SELECT voto FROM recensioni WHERE prenotazione_id = %s", (appuntamento_svolto,))
        assert cur.fetchall() == [(5,)]
    conn.close()


def test_recensione_di_un_appuntamento_altrui(client, utenti_accessi, appuntamento_svolto):
    _accedi(client, utenti_accessi["dipendente"])  # non è un cliente: area riservata
    assert client.get(f"/cliente/prenotazioni/{appuntamento_svolto}/recensione").status_code == 403

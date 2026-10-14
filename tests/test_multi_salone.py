"""
Isolamento tra saloni: nessun utente dello staff legge o modifica i dati di un altro salone,
e una prenotazione non può mescolare servizi o professionisti di saloni diversi.
"""
from datetime import UTC, date, datetime, timedelta

import pytest

from app.db import crea_connessione
from app.eccezioni import DatiNonValidiError, EmailGiaRegistrataError, RisorsaNonTrovataError
from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.pagamenti.finto import FakeProvider
from app.repository.orario import OrarioRepository
from app.repository.pagamento import PagamentoRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.salone import SaloneRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository
from app.servizi.calendario import CalendarioService
from app.servizi.disponibilita import DisponibilitaService
from app.servizi.prenotazione import PrenotazioneService
from app.servizi.salone import SaloneService
from app.servizi.saloni import SaloniService
from app.servizi.statistiche import StatisticheService

ADESSO = datetime(2026, 10, 13, 6, 0, tzinfo=UTC)  # martedì, 08:00 ora italiana
MERCOLEDI = "2026-10-14"
DOMINIO = "@multi.test"


@pytest.fixture
def altro(conn, altro_salone_test):
    """
    Un professionista e un servizio del secondo salone (annullati dal rollback).
    """
    return {
        "salone_id": altro_salone_test,
        "dipendente_id": UtenteRepository(conn).inserisci(Utente(
            "roma" + DOMINIO, "x", "Remo", "Romano", "3330000020", ruolo="dipendente",
            salone_id=altro_salone_test, riceve_prenotazioni=True,
        )),
        "servizio_id": ServizioRepository(conn).inserisci(Servizio("Taglio Roma", 30, 2500, salone_id=altro_salone_test)),
    }


# --- Prenotazione: tutto deve essere dello stesso salone ---

def _crea(conn, salone, salone_id, dipendente_id, servizi):
    return PrenotazioneService(conn, FakeProvider()).crea(
        salone["cliente"], salone_id, str(dipendente_id), [str(s) for s in servizi], MERCOLEDI, "10:00", "completo",
        ADESSO,
    )


def test_servizio_di_un_altro_salone_rifiutato(conn, salone, altro):
    with pytest.raises(DatiNonValidiError):
        _crea(conn, salone, salone["salone_id"], salone["dipendente_id"], [salone["taglio_id"], altro["servizio_id"]])


def test_professionista_di_un_altro_salone_rifiutato(conn, salone, altro):
    with pytest.raises(DatiNonValidiError):
        _crea(conn, salone, salone["salone_id"], altro["dipendente_id"], [salone["taglio_id"]])


def test_salone_inesistente_o_disattivato(conn, salone):
    with pytest.raises(RisorsaNonTrovataError):
        _crea(conn, salone, 0, salone["dipendente_id"], [salone["taglio_id"]])
    with conn.cursor() as cur:
        cur.execute("UPDATE saloni SET attivo = FALSE WHERE id = %s", (salone["salone_id"],))
    with pytest.raises(RisorsaNonTrovataError):
        _crea(conn, salone, salone["salone_id"], salone["dipendente_id"], [salone["taglio_id"]])


def test_prenotazione_salvata_con_il_suo_salone_e_il_suo_acconto(conn, salone, altro):
    with conn.cursor() as cur:
        cur.execute("UPDATE saloni SET percentuale_acconto = 50 WHERE id = %s", (altro["salone_id"],))
    prenotazione_id, _ = PrenotazioneService(conn, FakeProvider()).crea(
        salone["cliente"], altro["salone_id"], str(altro["dipendente_id"]), [str(altro["servizio_id"])],
        MERCOLEDI, "10:00", "acconto", ADESSO,
    )
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_id).salone_id == altro["salone_id"]
    with conn.cursor() as cur:
        cur.execute("SELECT importo_centesimi FROM pagamenti WHERE prenotazione_id = %s", (prenotazione_id,))
        assert cur.fetchone()[0] == 1250  # 50% di 25 €


def test_cliente_non_e_in_due_saloni_nello_stesso_momento(conn, salone, altro):
    PrenotazioneService(conn, FakeProvider()).crea(
        salone["cliente"], altro["salone_id"], str(altro["dipendente_id"]), [str(altro["servizio_id"])],
        MERCOLEDI, "10:00", "completo", ADESSO,
    )
    liberi = PrenotazioneService(conn, FakeProvider()).slot_per_scelta(
        salone["salone_id"], str(salone["dipendente_id"]), [str(salone["taglio_id"])], MERCOLEDI, ADESSO,
        salone["cliente"].id,
    )
    assert "10:00" not in [s.strftime("%H:%M") for s in liberi]


# --- Staff: solo il proprio salone ---

def _confermata_nell_altro_salone(conn, salone, altro) -> int:
    inizio = datetime(2026, 10, 14, 8, 0)
    return PrenotazioneRepository(conn).inserisci(Prenotazione(
        salone_id=altro["salone_id"], cliente_id=salone["cliente"].id, dipendente_id=altro["dipendente_id"],
        inizio=inizio, fine=inizio + timedelta(minutes=30), modalita_pagamento="completo", scade_il=inizio,
        stato="confermata", servizi=[ServizioPrenotato(altro["servizio_id"], "Taglio Roma", 30, 2500)],
    ))


def test_proprietario_non_annulla_prenotazioni_di_un_altro_salone(conn, salone, altro):
    proprietario = UtenteRepository(conn).leggi_per_id(UtenteRepository(conn).inserisci(Utente(
        "titolare" + DOMINIO, "x", "Tina", "Titolare", "3330000021", ruolo="proprietario",
        salone_id=salone["salone_id"],
    )))
    prenotazione_id = _confermata_nell_altro_salone(conn, salone, altro)
    servizio = PrenotazioneService(conn, FakeProvider())
    with pytest.raises(RisorsaNonTrovataError):
        servizio.prenotazione_per_il_salone(prenotazione_id, proprietario)
    with pytest.raises(RisorsaNonTrovataError):
        servizio.annulla_dal_salone(prenotazione_id, proprietario, ADESSO)
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_id).stato == "confermata"


def test_servizio_di_un_altro_salone_non_modificabile(conn, salone, altro):
    gestione = SaloneService(conn, salone["salone_id"])
    with pytest.raises(RisorsaNonTrovataError):
        gestione.leggi_servizio(altro["servizio_id"])
    with pytest.raises(RisorsaNonTrovataError):
        gestione.imposta_attivo(altro["servizio_id"], False)
    assert ServizioRepository(conn).leggi_per_id(altro["salone_id"], altro["servizio_id"]).attivo is True
    assert "Taglio Roma" not in [s.nome for s in gestione.elenca_servizi(solo_attivi=False)]


def test_statistiche_solo_del_proprio_salone(conn, salone, altro):
    _confermata_nell_altro_salone(conn, salone, altro)
    adesso = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
    assert StatisticheService(conn, salone["salone_id"]).riepilogo(30, adesso).prenotazioni == 0
    assert StatisticheService(conn, altro["salone_id"]).riepilogo(30, adesso).prenotazioni == 1


def test_orari_di_un_salone_non_cambiano_l_altro(conn, salone_test, altro_salone_test):
    CalendarioService(conn, salone_test).imposta_eccezione(MERCOLEDI, "no", [], "Ferie", ADESSO)
    assert DisponibilitaService(conn, salone_test).turni_del_giorno(date(2026, 10, 14)) == []
    assert DisponibilitaService(conn, altro_salone_test).turni_del_giorno(date(2026, 10, 14)) != []
    assert OrarioRepository(conn).leggi_eccezione(altro_salone_test, date(2026, 10, 14)) is None


def test_professionisti_elencati_per_salone(conn, salone, altro):
    utenti = UtenteRepository(conn)
    assert altro["dipendente_id"] not in [u.id for u in utenti.elenca_professionisti(salone["salone_id"])]
    assert [u.id for u in utenti.elenca_professionisti(altro["salone_id"])] == [altro["dipendente_id"]]


# --- Creazione di un salone ---

DATI_SALONE = {"nome": "Salone nuovo test", "indirizzo": "Via Roma 1, 80100 Napoli", "provincia": "na",
               "telefono": "+39 081 1234567", "coordinate": "40.8518, 14.2681", "percentuale_acconto": "25"}
DATI_PROPRIETARIO = {"email": "nuovo" + DOMINIO, "password": "password123", "nome": "Nadia",
                     "cognome": "Nuova", "telefono": "3330000022", "riceve_prenotazioni": True}


def test_salone_creato_con_proprietario_e_orari(conn):
    salone_id, proprietario_id = SaloniService(conn).crea_con_proprietario(DATI_SALONE, DATI_PROPRIETARIO)
    salone = SaloneRepository(conn).leggi_per_id(salone_id)
    proprietario = UtenteRepository(conn).leggi_per_id(proprietario_id)
    assert (salone.provincia, salone.percentuale_acconto, salone.telefono) == ("NA", 25, "+390811234567")
    assert str(salone.latitudine) == "40.851800" and str(salone.longitudine) == "14.268100"
    assert (proprietario.ruolo, proprietario.salone_id) == ("proprietario", salone_id)
    assert [(g, len(t)) for g, t in DisponibilitaService(conn, salone_id).orario_settimanale()][:2] == [(1, 0), (2, 2)]


@pytest.mark.parametrize("campo, valore", [
    ("provincia", "XX"),
    ("coordinate", "14.2681, 40.8518"),   # invertite: fuori dall'Italia
    ("coordinate", "40,8518 14,2681"),
    ("coordinate", ""),
    ("percentuale_acconto", "0"),
    ("percentuale_acconto", "100"),
    ("telefono", "abc"),
    ("nome", "  "),
])
def test_dati_del_salone_non_validi(conn, campo, valore):
    with pytest.raises(DatiNonValidiError):
        SaloniService(conn).crea_con_proprietario(DATI_SALONE | {campo: valore}, DATI_PROPRIETARIO)


def test_proprietario_non_valido_non_lascia_un_salone_senza_proprietario(conn, salone):
    with pytest.raises(EmailGiaRegistrataError):
        SaloniService(conn).crea_con_proprietario(DATI_SALONE, DATI_PROPRIETARIO | {"email": "cliente@salone.test"})
    assert SaloneRepository(conn).leggi_per_nome("Salone nuovo test") is None


# --- Pagine con dati salvati davvero (lette dall'app con un'altra connessione) ---

def _pulisci(connessione) -> None:
    with connessione.cursor() as cur:
        cur.execute("DELETE FROM pagamenti WHERE prenotazione_id IN (SELECT id FROM prenotazioni WHERE dipendente_id IN "
                    "(SELECT id FROM utenti WHERE email LIKE %s))", ("%" + DOMINIO,))
        cur.execute("DELETE FROM prenotazioni_servizi WHERE servizio_id IN "
                    "(SELECT id FROM servizi WHERE nome = 'Servizio multi test')")
        cur.execute("DELETE FROM prenotazioni WHERE dipendente_id IN (SELECT id FROM utenti WHERE email LIKE %s)",
                    ("%" + DOMINIO,))
        cur.execute("DELETE FROM servizi WHERE nome = 'Servizio multi test'")
        cur.execute("DELETE FROM utenti WHERE email LIKE %s", ("%" + DOMINIO,))
    connessione.commit()


@pytest.fixture
def dati_altro_salone(utenti_accessi, altro_salone_test):
    """
    Nel secondo salone, con commit reale: un professionista, un servizio e una prenotazione confermata
    fra 3 giorni, già pagata, del cliente dei test di accesso. Tutto cancellato alla fine.
    """
    connessione = crea_connessione()
    _pulisci(connessione)
    dipendente_id = UtenteRepository(connessione).inserisci(Utente(
        "pagine" + DOMINIO, "x", "Pino", "Pagine", "3330000023", ruolo="dipendente",
        salone_id=altro_salone_test, riceve_prenotazioni=True,
    ))
    servizio_id = ServizioRepository(connessione).inserisci(
        Servizio("Servizio multi test", 30, 1000, salone_id=altro_salone_test)
    )
    inizio = datetime.now(UTC).replace(tzinfo=None, microsecond=0) + timedelta(days=3)
    prenotazione_id = PrenotazioneRepository(connessione).inserisci(Prenotazione(
        salone_id=altro_salone_test, cliente_id=utenti_accessi["cliente"], dipendente_id=dipendente_id,
        inizio=inizio, fine=inizio + timedelta(minutes=30), modalita_pagamento="completo", scade_il=inizio,
        stato="confermata", servizi=[ServizioPrenotato(servizio_id, "Servizio multi test", 30, 1000)],
    ))
    PagamentoRepository(connessione).inserisci(Pagamento(
        tipo="online", importo_centesimi=1000, prenotazione_id=prenotazione_id, stato="completato",
    ))
    connessione.commit()
    yield {"dipendente_id": dipendente_id, "servizio_id": servizio_id, "prenotazione_id": prenotazione_id,
           "salone_id": altro_salone_test}
    _pulisci(connessione)
    connessione.close()


def _accedi(client, utente_id):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utente_id


def test_proprietario_non_apre_dati_di_un_altro_salone(client, utenti_accessi, dati_altro_salone):
    _accedi(client, utenti_accessi["proprietario"])
    assert client.get(f"/proprietario/dipendenti/{dati_altro_salone['dipendente_id']}").status_code == 404
    assert client.get(f"/proprietario/servizi/{dati_altro_salone['servizio_id']}/modifica").status_code == 404
    assert client.post(f"/proprietario/servizi/{dati_altro_salone['servizio_id']}/attivo",
                       data={"attivo": "0"}).status_code == 404
    url = f"/proprietario/prenotazioni/{dati_altro_salone['prenotazione_id']}/annulla"
    assert client.get(url).status_code == 404
    assert client.post(url).status_code == 404
    assert "Pino Pagine" not in client.get("/proprietario/dipendenti").text
    connessione = crea_connessione()
    assert PrenotazioneRepository(connessione).leggi_per_id(dati_altro_salone["prenotazione_id"]).stato == "confermata"
    assert ServizioRepository(connessione).leggi_per_id(
        dati_altro_salone["salone_id"], dati_altro_salone["servizio_id"]).attivo is True
    connessione.close()


def test_cliente_vede_le_prenotazioni_di_tutti_i_saloni(client, utenti_accessi, dati_altro_salone):
    _accedi(client, utenti_accessi["cliente"])
    pagina = client.get("/cliente/").text
    assert "Altro salone dei test" in pagina


def test_slot_con_servizio_di_un_altro_salone(client, utenti_accessi, salone_test, dati_altro_salone):
    _accedi(client, utenti_accessi["cliente"])
    risposta = client.get(f"/cliente/saloni/{salone_test}/slot", query_string={
        "dipendente_id": utenti_accessi["dipendente"], "data": (date.today() + timedelta(days=2)).isoformat(),
        "servizi": dati_altro_salone["servizio_id"],
    })
    assert risposta.status_code == 400
    assert "non è più disponibile" in risposta.json["errore"]


def test_pagine_pubbliche_del_salone(client, salone_test, dati_altro_salone):
    assert client.get(f"/saloni/{salone_test}").status_code == 200
    assert "Servizio multi test" not in client.get(f"/saloni/{salone_test}/servizi").text
    assert "Servizio multi test" in client.get(f"/saloni/{dati_altro_salone['salone_id']}/servizi").text
    assert client.get("/saloni/0").status_code == 404
    assert client.get("/saloni/0/servizi").status_code == 404

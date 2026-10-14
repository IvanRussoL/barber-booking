"""
Pagine di gestione del proprietario: orario settimanale, assenze e chiusure, dipendenti e saldo in sede.
La prenotazione di prova è di mercoledì 14/10/2026 dalle 10:00 alle 11:00 italiane (35,50 €, acconto 10,65 €).
"""
from datetime import UTC, date, datetime

import pytest
from flask import g, render_template_string

from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError
from app.modelli.utente import Utente
from app.pagamenti.finto import FakeProvider
from app.repository.orario import OrarioRepository
from app.repository.pagamento import PagamentoRepository
from app.repository.utente import UtenteRepository
from app.servizi.assenze import AssenzeService
from app.servizi.calendario import CalendarioService
from app.servizi.disponibilita import DisponibilitaService
from app.servizi.personale import PersonaleService
from app.servizi.prenotazione import PrenotazioneService

ADESSO = datetime(2026, 10, 13, 6, 0, tzinfo=UTC)  # martedì, 08:00 ora italiana
MERCOLEDI = "2026-10-14"
PRIMA_DELL_INIZIO = datetime(2026, 10, 14, 7, 59, tzinfo=UTC)
DOPO_L_INIZIO = datetime(2026, 10, 14, 8, 30, tzinfo=UTC)


@pytest.fixture
def provider():
    return FakeProvider()


def _confermata(conn, salone, provider) -> int:
    servizio = PrenotazioneService(conn, provider)
    prenotazione_id, url = servizio.crea(
        salone["cliente"], salone["salone_id"], str(salone["dipendente_id"]),
        [str(salone["taglio_id"]), str(salone["barba_id"])], MERCOLEDI, "10:00", "acconto", ADESSO,
    )
    servizio.conferma_pagamento(url.rsplit("/", 1)[1], ADESSO)
    return prenotazione_id


def _proprietario(conn, salone_id: int) -> Utente:
    utenti = UtenteRepository(conn)
    return utenti.leggi_per_id(utenti.inserisci(Utente(
        "titolare@gestione.test", "hash-finto", "Tina", "Titolare", "3330000009",
        ruolo="proprietario", salone_id=salone_id,
    )))


def _orari(turni) -> list[str]:
    return [f"{t.ora_inizio:%H:%M}-{t.ora_fine:%H:%M}" for t in turni]


# --- Orario settimanale ---

def test_orario_settimanale_modificato(conn, salone_test):
    calendario = CalendarioService(conn, salone_test)
    calendario.imposta_giorno_settimana(1, "si", [("10:00", "14:00"), ("", "")], ADESSO)
    calendario.imposta_giorno_settimana(2, "no", [], ADESSO)
    assert _orari(OrarioRepository(conn).turni_settimanali(salone_test, 1)) == ["10:00-14:00"]
    assert OrarioRepository(conn).turni_settimanali(salone_test, 2) == []


@pytest.mark.parametrize("giorno, aperto, orari", [
    (0, "si", [("09:00", "13:00")]),
    (8, "si", [("09:00", "13:00")]),
    (1, "forse", []),
    (1, "si", [("13:00", "09:00")]),
    (1, "si", [("09:15", "13:00")]),
])
def test_orario_settimanale_non_valido(conn, salone_test, giorno, aperto, orari):
    with pytest.raises(DatiNonValidiError):
        CalendarioService(conn, salone_test).imposta_giorno_settimana(giorno, aperto, orari, ADESSO)


def test_orario_settimanale_non_lascia_fuori_prenotazioni(conn, salone, provider):
    _confermata(conn, salone, provider)
    calendario = CalendarioService(conn, salone["salone_id"])
    with pytest.raises(DatiNonValidiError, match="1 prenotazione"):
        calendario.imposta_giorno_settimana(3, "si", [("15:00", "20:00")], ADESSO)
    calendario.imposta_giorno_settimana(3, "si", [("10:00", "13:00")], ADESSO)  # la prenotazione resta dentro
    # Una data con un orario proprio non dipende dal calendario settimanale.
    calendario.imposta_eccezione(MERCOLEDI, "si", [("09:00", "13:00"), ("", "")], "", ADESSO)
    calendario.imposta_giorno_settimana(3, "no", [], ADESSO)


# --- Assenze e chiusure ---

def test_assenza_di_un_professionista(conn, salone):
    AssenzeService(conn, salone["salone_id"]).aggiungi(str(salone["dipendente_id"]), "2026-10-15", "2026-10-16", "Ferie", ADESSO)
    disponibilita = DisponibilitaService(conn, salone["salone_id"])
    for giorno in (date(2026, 10, 15), date(2026, 10, 16)):
        assert disponibilita.slot_liberi(salone["dipendente_id"], giorno, 30, ADESSO) == []
        assert disponibilita.slot_liberi(salone["altro_dipendente_id"], giorno, 30, ADESSO) != []
    assert disponibilita.slot_liberi(salone["dipendente_id"], date(2026, 10, 17), 30, ADESSO) != []
    periodo = next(p for p in AssenzeService(conn, salone["salone_id"]).elenca(ADESSO) if p.nota == "Ferie")
    assert (periodo.dal, periodo.al, periodo.chi) == (date(2026, 10, 15), date(2026, 10, 16), "Dario Dipendente")


def test_chiusura_del_salone_di_un_giorno(conn, salone):
    AssenzeService(conn, salone["salone_id"]).aggiungi("", "2026-10-15", "", "Lavori", ADESSO)
    disponibilita = DisponibilitaService(conn, salone["salone_id"])
    for dipendente_id in (salone["dipendente_id"], salone["altro_dipendente_id"]):
        assert disponibilita.slot_liberi(dipendente_id, date(2026, 10, 15), 30, ADESSO) == []
        assert disponibilita.slot_liberi(dipendente_id, date(2026, 10, 16), 30, ADESSO) != []


def test_assenza_rifiutata_con_prenotazioni(conn, salone, provider):
    _confermata(conn, salone, provider)
    assenze = AssenzeService(conn, salone["salone_id"])
    with pytest.raises(DatiNonValidiError, match="1 prenotazione"):
        assenze.aggiungi(str(salone["dipendente_id"]), MERCOLEDI, MERCOLEDI, "", ADESSO)
    with pytest.raises(DatiNonValidiError, match="1 prenotazione"):
        assenze.aggiungi("", MERCOLEDI, MERCOLEDI, "", ADESSO)
    assenze.aggiungi(str(salone["altro_dipendente_id"]), MERCOLEDI, MERCOLEDI, "", ADESSO)  # l'altro è libero


@pytest.mark.parametrize("dal, al", [("2026-10-12", ""), ("2026-10-20", "2026-10-19"), ("ieri", ""), ("2026-10-20", "2027-12-31")])
def test_periodo_non_valido(conn, salone, dal, al):
    with pytest.raises(DatiNonValidiError):
        AssenzeService(conn, salone["salone_id"]).aggiungi("", dal, al, "", ADESSO)


def test_assenza_di_un_professionista_di_un_altro_salone(conn, salone, altro_salone_test):
    with pytest.raises(DatiNonValidiError):
        AssenzeService(conn, altro_salone_test).aggiungi(str(salone["dipendente_id"]), "2026-10-15", "", "", ADESSO)


def test_elimina_solo_nel_proprio_salone(conn, salone, altro_salone_test):
    AssenzeService(conn, salone["salone_id"]).aggiungi("", "2026-10-15", "", "Da togliere", ADESSO)
    periodo = next(p for p in AssenzeService(conn, salone["salone_id"]).elenca(ADESSO) if p.nota == "Da togliere")
    with pytest.raises(RisorsaNonTrovataError):
        AssenzeService(conn, altro_salone_test).elimina(periodo.id)
    AssenzeService(conn, salone["salone_id"]).elimina(periodo.id)
    assert all(p.id != periodo.id for p in AssenzeService(conn, salone["salone_id"]).elenca(ADESSO))


# --- Dipendenti ---

def _ids_professionisti(conn, salone_id: int) -> list[int]:
    return [u.id for u in UtenteRepository(conn).elenca_professionisti(salone_id)]


def test_crea_disattiva_e_riattiva_dipendente(conn, salone_test):
    personale = PersonaleService(conn, salone_test)
    nuovo_id = personale.crea_dipendente("nuovo@gestione.test", "provvisoria1", "Nino", "Nuovo", "+393330000010")
    nuovo = UtenteRepository(conn).leggi_per_id(nuovo_id)
    assert (nuovo.ruolo, nuovo.salone_id, nuovo.riceve_prenotazioni) == ("dipendente", salone_test, True)
    assert nuovo_id in _ids_professionisti(conn, salone_test)
    personale.imposta_attivo(nuovo_id, False, ADESSO)
    assert nuovo_id not in _ids_professionisti(conn, salone_test)
    assert nuovo_id in [u.id for u in personale.disattivati()]
    personale.imposta_attivo(nuovo_id, True, ADESSO)
    assert nuovo_id in _ids_professionisti(conn, salone_test)


def test_non_si_disattiva_chi_ha_appuntamenti(conn, salone, provider):
    _confermata(conn, salone, provider)
    with pytest.raises(DatiNonValidiError, match="appuntamenti in programma"):
        PersonaleService(conn, salone["salone_id"]).imposta_attivo(salone["dipendente_id"], False, ADESSO)


def test_dipendente_di_un_altro_salone_o_proprietario_non_trovati(conn, salone, altro_salone_test):
    with pytest.raises(RisorsaNonTrovataError):
        PersonaleService(conn, altro_salone_test).imposta_attivo(salone["dipendente_id"], False, ADESSO)
    titolare = _proprietario(conn, salone["salone_id"])
    with pytest.raises(RisorsaNonTrovataError):
        PersonaleService(conn, salone["salone_id"]).imposta_attivo(titolare.id, False, ADESSO)


# --- Saldo in sede ---

def test_saldo_in_sede_dopo_l_inizio(conn, salone, provider):
    prenotazione_id = _confermata(conn, salone, provider)
    titolare = _proprietario(conn, salone["salone_id"])
    servizio = PrenotazioneService(conn, provider)
    with pytest.raises(DatiNonValidiError):
        servizio.registra_saldo(prenotazione_id, titolare, PRIMA_DELL_INIZIO)  # si può ancora annullare
    assert servizio.registra_saldo(prenotazione_id, titolare, DOPO_L_INIZIO) == 3550 - 1065
    assert PagamentoRepository(conn).totale_pagato(prenotazione_id) == 3550
    with pytest.raises(DatiNonValidiError):
        servizio.registra_saldo(prenotazione_id, titolare, DOPO_L_INIZIO)  # già saldato


def test_saldo_solo_dal_proprietario_del_salone(conn, salone, provider, altro_salone_test):
    prenotazione_id = _confermata(conn, salone, provider)
    servizio = PrenotazioneService(conn, provider)
    dipendente = UtenteRepository(conn).leggi_per_id(salone["dipendente_id"])
    with pytest.raises(RisorsaNonTrovataError):
        servizio.registra_saldo(prenotazione_id, dipendente, DOPO_L_INIZIO)
    with pytest.raises(RisorsaNonTrovataError):
        servizio.registra_saldo(prenotazione_id, _proprietario(conn, altro_salone_test), DOPO_L_INIZIO)


def test_agenda_con_pagato_e_da_saldare(conn, salone, provider):
    _confermata(conn, salone, provider)
    servizio = PrenotazioneService(conn, provider)
    prima = servizio.agenda(salone["dipendente_id"], PRIMA_DELL_INIZIO)[0]
    dopo = servizio.agenda(salone["dipendente_id"], DOPO_L_INIZIO)[0]
    assert (prima.pagato_centesimi, prima.da_saldare(), prima.annullabile, prima.saldabile) == (1065, 2485, True, False)
    assert (dopo.annullabile, dopo.saldabile) == (False, True)


def test_pulsante_del_saldo_solo_nell_agenda_del_proprietario(app, conn, salone, provider):
    _confermata(conn, salone, provider)
    appuntamenti = PrenotazioneService(conn, provider).agenda(salone["dipendente_id"], DOPO_L_INIZIO)
    pagina = '{% set endpoint_annulla = "proprietario.annulla_prenotazione" %}{{ saldo }}{% include "agenda_elenco.html" %}'
    with app.test_request_context():
        g.utente = None
        proprietario = render_template_string(pagina.replace("{{ saldo }}", '{% set endpoint_saldo = "proprietario.registra_saldo" %}'),
                                              appuntamenti=appuntamenti, storico=[], fuso_orario="Europe/Rome")
        dipendente = render_template_string(pagina.replace("{{ saldo }}", ""),
                                            appuntamenti=appuntamenti, storico=[], fuso_orario="Europe/Rome")
    assert "Registra saldo di 24,85" in proprietario and "da pagare in sede 24,85" in proprietario
    assert "Registra saldo" not in dipendente and "da pagare in sede 24,85" in dipendente


# --- Pagine ---

def _entra(client, utenti_accessi, ruolo="proprietario"):
    with client.session_transaction() as sessione:
        sessione["utente_id"] = utenti_accessi[ruolo]


def test_pagine_di_gestione(client, utenti_accessi):
    _entra(client, utenti_accessi)
    assert "Orario del lunedì" in client.get("/proprietario/orari/settimana/1").text
    assert client.get("/proprietario/orari/settimana/8").status_code == 404
    assert client.get("/proprietario/assenze").status_code == 200
    assert client.get("/proprietario/dipendenti/nuovo").status_code == 200
    assert "Assenze e chiusure" in client.get("/proprietario/").text


def test_moduli_non_validi_rispondono_400(client, utenti_accessi):
    _entra(client, utenti_accessi)
    assert client.post("/proprietario/assenze", data={"chi": "", "dal": "2000-01-01"}).status_code == 400
    risposta = client.post("/proprietario/dipendenti/nuovo", data={
        "nome": "Nino", "cognome": "Nuovo", "email": "senza-chiocciola", "telefono": "3330000010", "password": "segreta-123",
    })
    assert risposta.status_code == 400 and "segreta-123" not in risposta.text  # la password non torna nella pagina
    assert client.post("/proprietario/orari/settimana/1", data={"aperto": "si", "inizio_1": "13:00", "fine_1": "09:00"}).status_code == 400

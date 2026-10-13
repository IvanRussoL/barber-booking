from datetime import UTC, datetime, timedelta

import pytest

from app.eccezioni import (AnnullamentoNonConsentitoError, DatiNonValidiError, RisorsaNonTrovataError,
                           SlotNonDisponibileError)
from app.pagamenti.finto import FakeProvider
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.servizio import ServizioRepository
from app.servizi.prenotazione import PrenotazioneService, calcola_acconto

ADESSO = datetime(2026, 10, 13, 6, 0, tzinfo=UTC)  # martedì, 08:00 ora italiana
MERCOLEDI = "2026-10-14"


@pytest.fixture
def provider():
    return FakeProvider()


def _crea(conn, salone, provider, ora="09:00", modalita="acconto", servizi=None, adesso=ADESSO, **altro):
    """
    Prenota mercoledì con Taglio e Barba (60 minuti, 35,50 €), salvo modifiche.
    """
    servizi = servizi or [str(salone["taglio_id"]), str(salone["barba_id"])]
    dati = {"dipendente_id": str(salone["dipendente_id"]), "giorno": MERCOLEDI} | altro
    return PrenotazioneService(conn, provider).crea(
        salone["cliente"], dati["dipendente_id"], servizi, dati["giorno"], ora, modalita, adesso
    )


def _pagamenti(conn, prenotazione_id) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tipo, importo_centesimi, stato FROM pagamenti WHERE prenotazione_id = %s ORDER BY id",
            (prenotazione_id,),
        )
        return cur.fetchall()


def _riferimento(url: str) -> str:
    return url.rsplit("/", 1)[1]


# --- Calcolo dell'acconto ---

@pytest.mark.parametrize("totale, percentuale, acconto", [
    (3550, 30, 1065), (1001, 30, 300), (1005, 30, 302), (1, 1, 1),
])
def test_calcola_acconto(totale, percentuale, acconto):
    assert calcola_acconto(totale, percentuale) == acconto


# --- Creazione ---

def test_prenotazione_creata_in_attesa_con_acconto(conn, salone, provider):
    prenotazione_id, url = _crea(conn, salone, provider)
    prenotazione = PrenotazioneRepository(conn).leggi_per_id(prenotazione_id)
    assert prenotazione.stato == "in_attesa_pagamento"
    assert prenotazione.inizio == datetime(2026, 10, 14, 7, 0)  # 09:00 italiane in UTC
    assert prenotazione.fine == datetime(2026, 10, 14, 8, 0)
    assert prenotazione.scade_il == datetime(2026, 10, 13, 6, 30)
    assert prenotazione.prezzo_totale() == 3550
    assert [s.nome for s in prenotazione.servizi] == ["Barba prova", "Taglio prova"]
    assert url == f"/cliente/pagamento/{_riferimento(url)}"
    assert _pagamenti(conn, prenotazione_id) == [("online", 1065, "in_attesa")]


def test_importo_completo(conn, salone, provider):
    prenotazione_id, _ = _crea(conn, salone, provider, modalita="completo")
    assert _pagamenti(conn, prenotazione_id) == [("online", 3550, "in_attesa")]


def test_prezzo_fissato_al_momento_della_prenotazione(conn, salone, provider):
    prenotazione_id, _ = _crea(conn, salone, provider)
    servizi = ServizioRepository(conn)
    taglio = servizi.leggi_per_id(salone["taglio_id"])
    taglio.prezzo_centesimi = 9900
    servizi.aggiorna(taglio)
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_id).prezzo_totale() == 3550


def test_slot_gia_preso_rifiutato(conn, salone, provider):
    _crea(conn, salone, provider, ora="10:00")
    with pytest.raises(SlotNonDisponibileError):
        _crea(conn, salone, provider, ora="10:30")  # si sovrappone a 10:00-11:00


@pytest.mark.parametrize("ora", ["09:15", "12:30", "13:00", "07:00"])
def test_orari_fuori_griglia_o_fuori_turno(conn, salone, provider, ora):
    with pytest.raises(SlotNonDisponibileError):
        _crea(conn, salone, provider, ora=ora)  # 60 minuti: 12:30 attraverserebbe la pausa


@pytest.mark.parametrize("modifica", [
    {"servizi": ["abc"]},
    {"servizi": ["999999"]},
    {"modalita": "gratis"},
    {"ora": "nove"},
    {"giorno": "domani"},
    {"dipendente_id": ""},
])
def test_dati_non_validi(conn, salone, provider, modifica):
    with pytest.raises(DatiNonValidiError):
        _crea(conn, salone, provider, **modifica)


def test_nessun_servizio_scelto(conn, salone, provider):
    with pytest.raises(DatiNonValidiError):
        PrenotazioneService(conn, provider).crea(
            salone["cliente"], str(salone["dipendente_id"]), [], MERCOLEDI, "09:00", "acconto", ADESSO
        )


def test_servizio_disattivato_non_prenotabile(conn, salone, provider):
    servizi = ServizioRepository(conn)
    barba = servizi.leggi_per_id(salone["barba_id"])
    barba.attivo = False
    servizi.aggiorna(barba)
    with pytest.raises(DatiNonValidiError):
        _crea(conn, salone, provider)


def test_cliente_non_prenotabile_come_professionista(conn, salone, provider):
    with pytest.raises(DatiNonValidiError):
        _crea(conn, salone, provider, dipendente_id=str(salone["cliente"].id))


# --- Pagamento ---

def test_pagamento_conferma_ed_e_idempotente(conn, salone, provider):
    prenotazione_id, url = _crea(conn, salone, provider)
    servizio = PrenotazioneService(conn, provider)
    assert servizio.conferma_pagamento(_riferimento(url), ADESSO + timedelta(minutes=5)) is True
    assert servizio.conferma_pagamento(_riferimento(url), ADESSO + timedelta(minutes=6)) is True
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_id).stato == "confermata"
    assert _pagamenti(conn, prenotazione_id) == [("online", 1065, "completato")]
    assert provider.rimborsi == []


def test_pagamento_arrivato_dopo_la_scadenza_rimborsato(conn, salone, provider):
    prenotazione_id, url = _crea(conn, salone, provider)
    servizio = PrenotazioneService(conn, provider)
    assert servizio.conferma_pagamento(_riferimento(url), ADESSO + timedelta(minutes=31)) is False
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_id).stato == "scaduta"
    assert _pagamenti(conn, prenotazione_id) == [
        ("online", 1065, "completato"), ("rimborso", 1065, "completato")
    ]
    assert provider.rimborsi == [(_riferimento(url), 1065)]


def test_uscita_dal_pagamento_libera_lo_slot(conn, salone, provider):
    prenotazione_id, url = _crea(conn, salone, provider, ora="10:00")
    PrenotazioneService(conn, provider).annulla_pagamento(_riferimento(url), ADESSO)
    prenotazione = PrenotazioneRepository(conn).leggi_per_id(prenotazione_id)
    assert (prenotazione.stato, prenotazione.annullata_da) == ("annullata", "cliente")
    assert _pagamenti(conn, prenotazione_id) == [("online", 1065, "fallito")]
    assert provider.sessioni_chiuse == [_riferimento(url)]
    _crea(conn, salone, provider, ora="10:00")  # lo stesso orario è di nuovo prenotabile


def test_pagamento_di_un_altro_cliente_non_trovato(conn, salone, provider):
    _, url = _crea(conn, salone, provider)
    with pytest.raises(RisorsaNonTrovataError):
        PrenotazioneService(conn, provider).pagamento_del_cliente(_riferimento(url), salone["dipendente_id"])


# --- Area cliente: storico e annullamento ---

def _confermata(conn, salone, provider, ora="10:00", modalita="acconto"):
    """
    Crea e paga una prenotazione di mercoledì (inizio alle 10:00 italiane = 08:00 UTC).
    """
    prenotazione_id, url = _crea(conn, salone, provider, ora=ora, modalita=modalita)
    PrenotazioneService(conn, provider).conferma_pagamento(_riferimento(url), ADESSO)
    return prenotazione_id, _riferimento(url)


def test_annullamento_rimborsa_quanto_pagato(conn, salone, provider):
    prenotazione_id, riferimento = _confermata(conn, salone, provider)
    rimborsato = PrenotazioneService(conn, provider).annulla_dal_cliente(
        prenotazione_id, salone["cliente"].id, ADESSO
    )
    prenotazione = PrenotazioneRepository(conn).leggi_per_id(prenotazione_id)
    assert rimborsato == 1065
    assert (prenotazione.stato, prenotazione.annullata_da) == ("annullata", "cliente")
    assert provider.rimborsi == [(riferimento, 1065)]
    assert _pagamenti(conn, prenotazione_id)[-1] == ("rimborso", 1065, "completato")


@pytest.mark.parametrize("minuti_prima, permesso", [(121, True), (120, True), (119, False)])
def test_regola_delle_due_ore(conn, salone, provider, minuti_prima, permesso):
    prenotazione_id, _ = _confermata(conn, salone, provider)
    adesso = datetime(2026, 10, 14, 8, 0, tzinfo=UTC) - timedelta(minutes=minuti_prima)
    servizio = PrenotazioneService(conn, provider)
    if permesso:
        servizio.annulla_dal_cliente(prenotazione_id, salone["cliente"].id, adesso)
    else:
        with pytest.raises(AnnullamentoNonConsentitoError):
            servizio.annulla_dal_cliente(prenotazione_id, salone["cliente"].id, adesso)


def test_non_si_annulla_due_volte(conn, salone, provider):
    prenotazione_id, _ = _confermata(conn, salone, provider)
    servizio = PrenotazioneService(conn, provider)
    servizio.annulla_dal_cliente(prenotazione_id, salone["cliente"].id, ADESSO)
    with pytest.raises(AnnullamentoNonConsentitoError):
        servizio.annulla_dal_cliente(prenotazione_id, salone["cliente"].id, ADESSO)
    assert len(provider.rimborsi) == 1


def test_prenotazione_di_un_altro_cliente_non_trovata(conn, salone, provider):
    prenotazione_id, _ = _confermata(conn, salone, provider)
    servizio = PrenotazioneService(conn, provider)
    with pytest.raises(RisorsaNonTrovataError):
        servizio.prenotazione_del_cliente(prenotazione_id, salone["dipendente_id"])
    with pytest.raises(RisorsaNonTrovataError):
        servizio.annulla_dal_cliente(prenotazione_id, salone["dipendente_id"], ADESSO)
    assert PrenotazioneRepository(conn).leggi_per_id(prenotazione_id).stato == "confermata"


def test_storico_con_pagato_e_senza_pagamenti_abbandonati(conn, salone, provider):
    confermata_id, _ = _confermata(conn, salone, provider, ora="10:00", modalita="completo")
    _, url = _crea(conn, salone, provider, ora="15:00")
    PrenotazioneService(conn, provider).annulla_pagamento(_riferimento(url), ADESSO)
    storico = PrenotazioneService(conn, provider).storico_cliente(salone["cliente"].id, ADESSO)
    assert [r.prenotazione.id for r in storico] == [confermata_id]
    assert storico[0].pagato_centesimi == 3550
    assert storico[0].professionista == "Dario Dipendente"
    assert storico[0].annullabile is True


def test_agenda_solo_del_professionista_e_confermate(conn, salone, provider):
    confermata_id, _ = _confermata(conn, salone, provider, ora="10:00")
    _crea(conn, salone, provider, ora="15:00")  # in attesa di pagamento: non in agenda
    servizio = PrenotazioneService(conn, provider)
    agenda = servizio.agenda(salone["dipendente_id"], ADESSO)
    assert [a.prenotazione.id for a in agenda] == [confermata_id]
    assert agenda[0].cliente.nome == "Carla"
    assert servizio.agenda(salone["altro_dipendente_id"], ADESSO) == []


# --- Un cliente non può avere due appuntamenti sovrapposti ---

def test_cliente_non_prenota_due_appuntamenti_sovrapposti(conn, salone, provider):
    _confermata(conn, salone, provider, ora="10:00")  # 10:00-11:00 con Dario
    with pytest.raises(SlotNonDisponibileError):
        _crea(conn, salone, provider, ora="10:30", dipendente_id=str(salone["altro_dipendente_id"]))
    _crea(conn, salone, provider, ora="11:00", dipendente_id=str(salone["altro_dipendente_id"]))


def test_orari_del_cliente_occupati_non_proposti(conn, salone, provider):
    _confermata(conn, salone, provider, ora="10:00")
    servizio = PrenotazioneService(conn, provider)
    altro = str(salone["altro_dipendente_id"])
    taglio = [str(salone["taglio_id"])]
    per_il_cliente = [s.strftime("%H:%M") for s in servizio.slot_per_scelta(
        altro, taglio, MERCOLEDI, ADESSO, salone["cliente"].id)]
    per_tutti = [s.strftime("%H:%M") for s in servizio.slot_per_scelta(altro, taglio, MERCOLEDI, ADESSO)]
    assert "10:00" not in per_il_cliente and "10:30" not in per_il_cliente and "11:00" in per_il_cliente
    assert "10:00" in per_tutti

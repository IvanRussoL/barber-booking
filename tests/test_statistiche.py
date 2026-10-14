from datetime import UTC, datetime

import pytest

from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.repository.pagamento import PagamentoRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.servizi.statistiche import StatisticheService, periodo_valido

ADESSO = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def _prenotazione(conn, salone, dipendente, inizio_utc, prezzo, stato="confermata", pagato=None):
    """
    Inserisce una prenotazione di 30 minuti con un pagamento online completato.
    """
    prenotazione_id = PrenotazioneRepository(conn).inserisci(Prenotazione(
        salone_id=salone["salone_id"], cliente_id=salone["cliente"].id, dipendente_id=salone[dipendente], inizio=inizio_utc,
        fine=inizio_utc.replace(minute=30), modalita_pagamento="completo", scade_il=inizio_utc, stato=stato,
        servizi=[ServizioPrenotato(salone["taglio_id"], "Taglio prova", 30, prezzo)],
    ))
    PagamentoRepository(conn).inserisci(Pagamento(
        tipo="online", importo_centesimi=pagato or prezzo, prenotazione_id=prenotazione_id,
        stato="completato", creato_il=datetime(2026, 10, 1, 9, 0),
    ))
    return prenotazione_id


@pytest.fixture
def dati(conn, salone):
    # Due prenotazioni di Dario e una di Alba nel periodo; una annullata e una troppo vecchia non contano.
    _prenotazione(conn, salone, "dipendente_id", datetime(2026, 10, 2, 8, 0), 2000)    # 10:00 italiane
    _prenotazione(conn, salone, "dipendente_id", datetime(2026, 10, 9, 15, 0), 3000)   # 17:00 italiane
    _prenotazione(conn, salone, "altro_dipendente_id", datetime(2026, 10, 9, 8, 0), 1000)
    _prenotazione(conn, salone, "dipendente_id", datetime(2026, 10, 10, 8, 0), 5000, stato="annullata")
    _prenotazione(conn, salone, "dipendente_id", datetime(2026, 6, 1, 8, 0), 9900)
    return salone


@pytest.mark.parametrize("valore, giorni", [("7", 7), ("30", 30), ("365", 365), ("90", 30), (None, 30), ("abc", 30)])
def test_periodo_valido(valore, giorni):
    assert periodo_valido(valore) == giorni


def test_riepilogo_del_salone(conn, dati):
    riepilogo = StatisticheService(conn, dati["salone_id"]).riepilogo(30, ADESSO)
    assert riepilogo.prenotazioni == 3
    assert riepilogo.clienti_unici == 1
    assert riepilogo.valore_servizi_centesimi == 6000
    assert riepilogo.valore_medio_centesimi == 2000
    # incasso: tutti i pagamenti completati registrati nel periodo, anche quello della prenotazione annullata
    assert riepilogo.incasso_netto_centesimi == 2000 + 3000 + 1000 + 5000 + 9900


def test_riepilogo_del_professionista(conn, dati):
    riepilogo = StatisticheService(conn, dati["salone_id"]).riepilogo(30, ADESSO, dipendente_id=dati["dipendente_id"])
    assert (riepilogo.prenotazioni, riepilogo.valore_servizi_centesimi) == (2, 5000)
    assert riepilogo.incasso_netto_centesimi is None


def test_per_professionista_e_fasce(conn, dati):
    servizio = StatisticheService(conn, dati["salone_id"])
    tabella = servizio.per_professionista(30, ADESSO)
    assert tabella["professionista"].tolist() == ["Dario Dipendente", "Alba Altra"]
    assert tabella["prenotazioni"].tolist() == [2, 1]
    assert servizio.per_ora_di_inizio(30, ADESSO).to_dict() == {10: 2, 17: 1}


def test_grafici_png_anche_senza_dati(conn, dati):
    servizio = StatisticheService(conn, dati["salone_id"])
    for immagine in (servizio.grafico_professionisti(30, ADESSO), servizio.grafico_fasce(30, ADESSO),
                     servizio.grafico_andamento(30, datetime(2020, 1, 1, tzinfo=UTC))):
        assert immagine.startswith(b"\x89PNG")

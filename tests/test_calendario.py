from datetime import UTC, date, datetime

import pytest

from app.eccezioni import DatiNonValidiError
from app.modelli.prenotazione import Prenotazione
from app.repository.orario import OrarioRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.servizi.calendario import CalendarioService, turni_validi
from app.servizi.disponibilita import DisponibilitaService
from app.servizi.festivita import giornate_a_rischio, pasqua

ADESSO = datetime(2026, 10, 13, 6, 0, tzinfo=UTC)  # martedì, 08:00 ora italiana
MERCOLEDI = "2026-10-14"


def _orari(turni) -> list[str]:
    return [f"{t.ora_inizio:%H:%M}-{t.ora_fine:%H:%M}" for t in turni]


# --- Festività ---

@pytest.mark.parametrize("anno, attesa", [
    (2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5)), (2027, date(2027, 3, 28)),
])
def test_pasqua(anno, attesa):
    assert pasqua(anno) == attesa


def test_giornate_a_rischio():
    giornate = giornate_a_rischio(2027)
    assert {date(2027, 12, 24), date(2027, 12, 25), date(2027, 12, 26), date(2027, 1, 6)} <= giornate
    assert {date(2027, 3, 28), date(2027, 3, 29)} <= giornate  # Pasqua e Pasquetta
    assert date(2027, 3, 10) not in giornate


# --- Date da definire ---

def test_festivita_in_un_giorno_aperto_da_definire(conn):
    disponibilita = DisponibilitaService(conn)
    assert disponibilita.da_definire(date(2026, 12, 24)) is True   # giovedì: di solito aperto
    assert disponibilita.da_definire(date(2027, 3, 29)) is False   # Pasquetta di lunedì: già chiuso
    assert disponibilita.da_definire(date(2026, 12, 23)) is False  # giorno qualsiasi


def test_festivita_da_definire_resta_prenotabile(conn):
    # Finché il proprietario non decide valgono i turni settimanali.
    assert _orari(DisponibilitaService(conn).turni_del_giorno(date(2026, 12, 24))) == ["09:00-13:00", "15:00-23:00"]


def test_giornate_speciali(conn):
    CalendarioService(conn).imposta_eccezione("2026-12-24", "si", [("09:00", "13:00"), ("", "")], "Vigilia", ADESSO)
    CalendarioService(conn).imposta_eccezione("2026-12-25", "no", [], "", ADESSO)
    speciali = DisponibilitaService(conn).giornate_speciali(date(2026, 12, 20), date(2026, 12, 31))
    assert [(g.data.day, g.stato) for g in speciali] == [
        (24, "aperto"), (25, "chiuso"), (26, "da_definire"), (31, "da_definire"),
    ]
    assert _orari(speciali[0].turni) == ["09:00-13:00"]
    assert speciali[0].nota == "Vigilia"


# --- Controllo dei turni del modulo ---

@pytest.mark.parametrize("orari", [
    [("", ""), ("", "")],                     # primo turno obbligatorio
    [("09:15", "13:00"), ("", "")],           # fuori dalla griglia
    [("13:00", "09:00"), ("", "")],           # fine prima dell'inizio
    [("09:00", "13:00"), ("12:00", "18:00")],  # secondo turno sovrapposto
    [("09:00", "13:00"), ("15:00", "")],      # secondo turno a metà
    [("nove", "13:00"), ("", "")],
])
def test_turni_non_validi(orari):
    with pytest.raises(DatiNonValidiError):
        turni_validi(orari)


def test_turni_validi():
    assert _orari(turni_validi([("09:00", "13:00"), ("15:30", "19:00")])) == ["09:00-13:00", "15:30-19:00"]


# --- Modifica degli orari di una data ---

def test_chiusura_di_una_data(conn, salone):
    CalendarioService(conn).imposta_eccezione(MERCOLEDI, "no", [], "Ferie", ADESSO)
    assert DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], date(2026, 10, 14), 30, ADESSO) == []


def test_orario_ridotto_e_ripristino(conn):
    calendario = CalendarioService(conn)
    calendario.imposta_eccezione(MERCOLEDI, "si", [("10:00", "12:00"), ("", "")], "", ADESSO)
    assert _orari(calendario.disponibilita.turni_del_giorno(date(2026, 10, 14))) == ["10:00-12:00"]
    calendario.rimuovi_eccezione(MERCOLEDI, ADESSO)
    assert OrarioRepository(conn).leggi_eccezione(date(2026, 10, 14)) is None


@pytest.mark.parametrize("data", ["2026-10-12", "ieri", ""])
def test_data_passata_o_non_valida(conn, data):
    with pytest.raises(DatiNonValidiError):
        CalendarioService(conn).imposta_eccezione(data, "no", [], "", ADESSO)


def test_prenotazioni_fuori_dai_nuovi_orari_bloccano_la_modifica(conn, salone):
    PrenotazioneRepository(conn).inserisci(Prenotazione(
        cliente_id=salone["cliente"].id, dipendente_id=salone["dipendente_id"],
        inizio=datetime(2026, 10, 14, 13, 0), fine=datetime(2026, 10, 14, 13, 30),  # 15:00 italiane
        modalita_pagamento="completo", scade_il=datetime(2026, 10, 14, 13, 0), stato="confermata",
    ))
    calendario = CalendarioService(conn)
    with pytest.raises(DatiNonValidiError, match="1 prenotazione fuori"):
        calendario.imposta_eccezione(MERCOLEDI, "no", [], "", ADESSO)
    with pytest.raises(DatiNonValidiError):
        calendario.imposta_eccezione(MERCOLEDI, "si", [("09:00", "13:00"), ("", "")], "", ADESSO)
    calendario.imposta_eccezione(MERCOLEDI, "si", [("09:00", "13:00"), ("15:00", "18:00")], "", ADESSO)

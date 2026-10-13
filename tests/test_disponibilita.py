from datetime import UTC, date, datetime, time

import pytest

from app.eccezioni import DatiNonValidiError
from app.modelli.prenotazione import Prenotazione
from app.repository.prenotazione import PrenotazioneRepository
from app.servizi.disponibilita import DisponibilitaService, in_utc

# Martedì 13 ottobre 2026 alle 08:00 ora italiana (06:00 UTC, ora legale).
ADESSO = datetime(2026, 10, 13, 6, 0, tzinfo=UTC)
MERCOLEDI = date(2026, 10, 14)
LUNEDI = date(2026, 10, 19)


def _orari(liberi: list[datetime]) -> list[str]:
    return [inizio.strftime("%H:%M") for inizio in liberi]


def _inserisci_prenotazione(conn, salone, inizio_utc, fine_utc, stato="confermata", scade_il=None):
    PrenotazioneRepository(conn).inserisci(Prenotazione(
        cliente_id=salone["cliente"].id, dipendente_id=salone["dipendente_id"],
        inizio=inizio_utc, fine=fine_utc, modalita_pagamento="completo",
        scade_il=scade_il or inizio_utc, stato=stato,
    ))


def _esegui(conn, sql, parametri):
    with conn.cursor() as cur:
        cur.execute(sql, parametri)


# --- Finestra e turni ---

def test_finestra_fino_alla_fine_del_terzo_mese_successivo(conn):
    assert DisponibilitaService(conn).finestra(ADESSO) == (date(2026, 10, 13), date(2027, 1, 31))


@pytest.mark.parametrize("giorno", [date(2026, 10, 12), date(2027, 2, 1)])
def test_date_fuori_dalla_finestra_rifiutate(conn, salone, giorno):
    with pytest.raises(DatiNonValidiError):
        DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], giorno, 30, ADESSO)


def test_giorno_normale_due_turni(conn, salone):
    liberi = _orari(DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert len(liberi) == 8 + 16
    assert liberi[0] == "09:00" and liberi[-1] == "22:30"
    assert "12:30" in liberi and "13:00" not in liberi and "15:00" in liberi


def test_appuntamento_lungo_non_attraversa_la_pausa(conn, salone):
    liberi = _orari(DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], MERCOLEDI, 60, ADESSO))
    assert "12:00" in liberi and "12:30" not in liberi
    assert "22:00" in liberi and "22:30" not in liberi


def test_lunedi_chiuso(conn, salone):
    assert DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], LUNEDI, 30, ADESSO) == []


def test_oggi_solo_orari_futuri(conn, salone):
    adesso = datetime(2026, 10, 13, 8, 15, tzinfo=UTC)  # 10:15 ora italiana
    liberi = _orari(DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], adesso.date(), 30, adesso))
    assert liberi[0] == "10:30"


def test_eccezione_chiusa_e_eccezione_aperta(conn, salone):
    _esegui(conn, "INSERT INTO eccezioni_date (data, aperto) VALUES (%s, FALSE)", (MERCOLEDI,))
    _esegui(conn, "INSERT INTO eccezioni_date (data, aperto) VALUES (%s, TRUE)", (LUNEDI,))
    _esegui(conn, "INSERT INTO eccezioni_turni (data, ora_inizio, ora_fine) VALUES (%s, '10:00', '12:00')", (LUNEDI,))
    disponibilita = DisponibilitaService(conn)
    assert disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO) == []
    assert _orari(disponibilita.slot_liberi(salone["dipendente_id"], LUNEDI, 30, ADESSO)) == [
        "10:00", "10:30", "11:00", "11:30"
    ]


def test_cambio_ora_legale_convertito_in_utc(conn, salone):
    domenica = date(2026, 10, 25)  # torna l'ora solare: le 09:00 italiane sono le 08:00 UTC
    primo = DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], domenica, 30, ADESSO)[0]
    assert primo.time() == time(9, 0)
    assert in_utc(primo) == datetime(2026, 10, 25, 8, 0)


# --- Prenotazioni, assenze e chiusure ---

def test_prenotazione_confermata_occupa_gli_slot(conn, salone):
    # 10:00-11:00 ora italiana = 08:00-09:00 UTC
    _inserisci_prenotazione(conn, salone, datetime(2026, 10, 14, 8, 0), datetime(2026, 10, 14, 9, 0))
    disponibilita = DisponibilitaService(conn)
    da_30 = _orari(disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    da_60 = _orari(disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 60, ADESSO))
    assert "09:30" in da_30 and "10:00" not in da_30 and "10:30" not in da_30 and "11:00" in da_30
    assert "09:00" in da_60 and "09:30" not in da_60 and "11:00" in da_60


def test_altro_dipendente_libero(conn, salone):
    _inserisci_prenotazione(conn, salone, datetime(2026, 10, 14, 8, 0), datetime(2026, 10, 14, 9, 0))
    liberi = _orari(DisponibilitaService(conn).slot_liberi(salone["altro_dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert "10:00" in liberi


@pytest.mark.parametrize("scade_il, occupa", [
    (datetime(2026, 10, 13, 6, 20), True),   # scade tra 20 minuti: blocca ancora lo slot
    (datetime(2026, 10, 13, 5, 50), False),  # scaduta 10 minuti fa: slot libero
])
def test_prenotazione_in_attesa_occupa_finche_non_scade(conn, salone, scade_il, occupa):
    _inserisci_prenotazione(conn, salone, datetime(2026, 10, 14, 8, 0), datetime(2026, 10, 14, 8, 30),
                            stato="in_attesa_pagamento", scade_il=scade_il)
    liberi = _orari(DisponibilitaService(conn).slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert ("10:00" not in liberi) == occupa


def test_assenza_e_chiusura_del_salone(conn, salone):
    _esegui(conn, "INSERT INTO indisponibilita (dipendente_id, inizio, fine) VALUES (%s, %s, %s)",
            (salone["dipendente_id"], datetime(2026, 10, 14, 7, 0), datetime(2026, 10, 14, 11, 0)))
    _esegui(conn, "INSERT INTO indisponibilita (dipendente_id, inizio, fine) VALUES (NULL, %s, %s)",
            (datetime(2026, 10, 15, 0, 0), datetime(2026, 10, 16, 0, 0)))
    disponibilita = DisponibilitaService(conn)
    mattina_assente = _orari(disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert mattina_assente[0] == "15:00"
    assert disponibilita.slot_liberi(salone["altro_dipendente_id"], date(2026, 10, 15), 30, ADESSO) == []

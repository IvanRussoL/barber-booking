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
        salone_id=salone["salone_id"], cliente_id=salone["cliente"].id, dipendente_id=salone["dipendente_id"],
        inizio=inizio_utc, fine=fine_utc, modalita_pagamento="completo",
        scade_il=scade_il or inizio_utc, stato=stato,
    ))


def _esegui(conn, sql, parametri):
    with conn.cursor() as cur:
        cur.execute(sql, parametri)


# --- Finestra e turni ---

def test_finestra_fino_alla_fine_del_terzo_mese_successivo(conn, salone_test):
    assert DisponibilitaService(conn, salone_test).finestra(ADESSO) == (date(2026, 10, 13), date(2027, 1, 31))


@pytest.mark.parametrize("giorno", [date(2026, 10, 12), date(2027, 2, 1)])
def test_date_fuori_dalla_finestra_rifiutate(conn, salone, giorno, salone_test):
    with pytest.raises(DatiNonValidiError):
        DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], giorno, 30, ADESSO)


def test_giorno_normale_due_turni(conn, salone, salone_test):
    liberi = _orari(DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert len(liberi) == 8 + 16
    assert liberi[0] == "09:00" and liberi[-1] == "22:30"
    assert "12:30" in liberi and "13:00" not in liberi and "15:00" in liberi


def test_appuntamento_lungo_non_attraversa_la_pausa(conn, salone, salone_test):
    liberi = _orari(DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], MERCOLEDI, 60, ADESSO))
    assert "12:00" in liberi and "12:30" not in liberi
    assert "22:00" in liberi and "22:30" not in liberi


def test_lunedi_chiuso(conn, salone, salone_test):
    assert DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], LUNEDI, 30, ADESSO) == []


def test_oggi_solo_orari_futuri(conn, salone, salone_test):
    adesso = datetime(2026, 10, 13, 8, 15, tzinfo=UTC)  # 10:15 ora italiana
    liberi = _orari(DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], adesso.date(), 30, adesso))
    assert liberi[0] == "10:30"


def test_eccezione_chiusa_e_eccezione_aperta(conn, salone, salone_test):
    _esegui(conn, "INSERT INTO eccezioni_date (salone_id, data, aperto) VALUES (%s, %s, FALSE)", (salone_test, MERCOLEDI))
    _esegui(conn, "INSERT INTO eccezioni_date (salone_id, data, aperto) VALUES (%s, %s, TRUE)", (salone_test, LUNEDI))
    _esegui(conn, "INSERT INTO eccezioni_turni (salone_id, data, ora_inizio, ora_fine) VALUES (%s, %s, '10:00', '12:00')",
            (salone_test, LUNEDI))
    disponibilita = DisponibilitaService(conn, salone_test)
    assert disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO) == []
    assert _orari(disponibilita.slot_liberi(salone["dipendente_id"], LUNEDI, 30, ADESSO)) == [
        "10:00", "10:30", "11:00", "11:30"
    ]


def test_cambio_ora_legale_convertito_in_utc(conn, salone, salone_test):
    domenica = date(2026, 10, 25)  # torna l'ora solare: le 09:00 italiane sono le 08:00 UTC
    primo = DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], domenica, 30, ADESSO)[0]
    assert primo.time() == time(9, 0)
    assert in_utc(primo) == datetime(2026, 10, 25, 8, 0)


# --- Prenotazioni, assenze e chiusure ---

def test_prenotazione_confermata_occupa_gli_slot(conn, salone, salone_test):
    # 10:00-11:00 ora italiana = 08:00-09:00 UTC
    _inserisci_prenotazione(conn, salone, datetime(2026, 10, 14, 8, 0), datetime(2026, 10, 14, 9, 0))
    disponibilita = DisponibilitaService(conn, salone_test)
    da_30 = _orari(disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    da_60 = _orari(disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 60, ADESSO))
    assert "09:30" in da_30 and "10:00" not in da_30 and "10:30" not in da_30 and "11:00" in da_30
    assert "09:00" in da_60 and "09:30" not in da_60 and "11:00" in da_60


def test_altro_dipendente_libero(conn, salone, salone_test):
    _inserisci_prenotazione(conn, salone, datetime(2026, 10, 14, 8, 0), datetime(2026, 10, 14, 9, 0))
    liberi = _orari(DisponibilitaService(conn, salone_test).slot_liberi(salone["altro_dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert "10:00" in liberi


@pytest.mark.parametrize("scade_il, occupa", [
    (datetime(2026, 10, 13, 6, 20), True),   # scade tra 20 minuti: blocca ancora lo slot
    (datetime(2026, 10, 13, 5, 50), False),  # scaduta 10 minuti fa: slot libero
])
def test_prenotazione_in_attesa_occupa_finche_non_scade(conn, salone, scade_il, occupa, salone_test):
    _inserisci_prenotazione(conn, salone, datetime(2026, 10, 14, 8, 0), datetime(2026, 10, 14, 8, 30),
                            stato="in_attesa_pagamento", scade_il=scade_il)
    liberi = _orari(DisponibilitaService(conn, salone_test).slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert ("10:00" not in liberi) == occupa


def test_assenza_e_chiusura_del_salone(conn, salone, salone_test):
    _esegui(conn, "INSERT INTO indisponibilita (salone_id, dipendente_id, inizio, fine) VALUES (%s, %s, %s, %s)",
            (salone_test, salone["dipendente_id"], datetime(2026, 10, 14, 7, 0), datetime(2026, 10, 14, 11, 0)))
    _esegui(conn, "INSERT INTO indisponibilita (salone_id, dipendente_id, inizio, fine) VALUES (%s, NULL, %s, %s)",
            (salone_test, datetime(2026, 10, 15, 0, 0), datetime(2026, 10, 16, 0, 0)))
    disponibilita = DisponibilitaService(conn, salone_test)
    mattina_assente = _orari(disponibilita.slot_liberi(salone["dipendente_id"], MERCOLEDI, 30, ADESSO))
    assert mattina_assente[0] == "15:00"
    assert disponibilita.slot_liberi(salone["altro_dipendente_id"], date(2026, 10, 15), 30, ADESSO) == []


# --- Orari per la pagina pubblica ---

@pytest.mark.parametrize("adesso_utc, aperto, testo", [
    (datetime(2026, 10, 13, 8, 0, tzinfo=UTC), True, "Aperto ora · chiude alle 13:00"),          # mar 10:00
    (datetime(2026, 10, 13, 11, 30, tzinfo=UTC), False, "Chiuso ora · riapre oggi alle 15:00"),  # mar 13:30
    (datetime(2026, 10, 13, 21, 30, tzinfo=UTC), False, "Chiuso ora · riapre domani alle 09:00"),  # mar 23:30
    (datetime(2026, 10, 18, 21, 30, tzinfo=UTC), False, "Chiuso ora · riapre mar alle 09:00"),   # dom 23:30, lun chiuso
])
def test_stato_apertura(conn, adesso_utc, aperto, testo, salone_test):
    assert DisponibilitaService(conn, salone_test).stato_apertura(adesso_utc) == (aperto, testo)


def test_stato_apertura_con_eccezione_chiusa(conn, salone_test):
    _esegui(conn, "INSERT INTO eccezioni_date (salone_id, data, aperto) VALUES (%s, %s, FALSE)",
            (salone_test, date(2026, 10, 13)))
    adesso = datetime(2026, 10, 13, 8, 0, tzinfo=UTC)  # martedì 10:00, ma oggi è chiuso per eccezione
    assert DisponibilitaService(conn, salone_test).stato_apertura(adesso) == (False, "Chiuso ora · riapre domani alle 09:00")


def test_orario_settimanale(conn, salone_test):
    orario = dict(DisponibilitaService(conn, salone_test).orario_settimanale())
    assert orario[1] == []
    assert [(t.ora_inizio, t.ora_fine) for t in orario[2]] == [(time(9, 0), time(13, 0)), (time(15, 0), time(23, 0))]

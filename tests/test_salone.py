import pytest

from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError, ServizioGiaEsistenteError
from app.formato import formatta_durata, formatta_euro
from app.servizi.salone import SaloneService
from app.servizi.validazione import euro_in_centesimi


# --- Conversioni e filtri ---

@pytest.mark.parametrize("testo, centesimi", [
    ("25", 2500), ("25,5", 2550), ("25.50", 2550), (" 0,05 ", 5), ("99999,99", 9999999),
])
def test_euro_in_centesimi(testo, centesimi):
    assert euro_in_centesimi(testo, "prezzo") == centesimi


@pytest.mark.parametrize("testo", ["", "abc", "25,555", "-5", "25,", "1e3", "100000"])
def test_euro_non_validi(testo):
    with pytest.raises(DatiNonValidiError):
        euro_in_centesimi(testo, "prezzo")


def test_filtri_euro_e_durata():
    assert formatta_euro(2550) == "25,50 €"
    assert formatta_euro(5) == "0,05 €"
    assert formatta_durata(30) == "30 min"
    assert formatta_durata(90) == "1 h 30 min"
    assert formatta_durata(120) == "2 h"


# --- Servizi ---

def test_servizio_creato_con_prezzo_in_centesimi(conn, salone_test):
    salone = SaloneService(conn, salone_test)
    servizio = salone.leggi_servizio(salone.crea_servizio(" Taglio test ", "", "30", "15,50"))
    assert servizio.nome == "Taglio test"
    assert servizio.descrizione is None
    assert servizio.durata_minuti == 30
    assert servizio.prezzo_centesimi == 1550
    assert servizio.attivo is True


@pytest.mark.parametrize("campo, valore", [
    ("nome", "  "),
    ("durata_minuti", "45"),
    ("durata_minuti", "0"),
    ("durata_minuti", "510"),
    ("durata_minuti", "trenta"),
    ("prezzo_euro", "0"),
    ("prezzo_euro", "dieci"),
])
def test_dati_del_servizio_non_validi(conn, campo, valore, salone_test):
    dati = {"nome": "Servizio test", "descrizione": "", "durata_minuti": "30", "prezzo_euro": "10"}
    with pytest.raises(DatiNonValidiError):
        SaloneService(conn, salone_test).crea_servizio(**(dati | {campo: valore}))


def test_nome_gia_usato_anche_con_maiuscole_diverse(conn, salone_test):
    salone = SaloneService(conn, salone_test)
    salone.crea_servizio("Barba test", "", "30", "10")
    with pytest.raises(ServizioGiaEsistenteError):
        salone.crea_servizio("BARBA TEST", "", "60", "20")


def test_modifica_mantiene_lo_stato_e_permette_lo_stesso_nome(conn, salone_test):
    salone = SaloneService(conn, salone_test)
    servizio_id = salone.crea_servizio("Colore test", "", "90", "40")
    salone.imposta_attivo(servizio_id, False)
    salone.modifica_servizio(servizio_id, "Colore test", "Con piega", "120", "45")
    servizio = salone.leggi_servizio(servizio_id)
    assert (servizio.durata_minuti, servizio.prezzo_centesimi) == (120, 4500)
    assert servizio.descrizione == "Con piega"
    assert servizio.attivo is False


def test_modifica_con_il_nome_di_un_altro_servizio(conn, salone_test):
    salone = SaloneService(conn, salone_test)
    salone.crea_servizio("Primo test", "", "30", "10")
    secondo_id = salone.crea_servizio("Secondo test", "", "30", "10")
    with pytest.raises(ServizioGiaEsistenteError):
        salone.modifica_servizio(secondo_id, "Primo test", "", "30", "10")


def test_servizio_disattivato_sparisce_dal_listino_pubblico(conn, salone_test):
    salone = SaloneService(conn, salone_test)
    servizio_id = salone.crea_servizio("Shampoo test", "", "30", "5")
    salone.imposta_attivo(servizio_id, False)
    assert "Shampoo test" not in [s.nome for s in salone.elenca_servizi()]
    assert "Shampoo test" in [s.nome for s in salone.elenca_servizi(solo_attivi=False)]


def test_servizio_inesistente(conn, salone_test):
    with pytest.raises(RisorsaNonTrovataError):
        SaloneService(conn, salone_test).leggi_servizio(0)

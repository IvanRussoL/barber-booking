"""
Ricerca dei saloni per regione e provincia e vicino a una posizione.
I due saloni dei test sono a Napoli (NA) e a Roma (RM), a circa 190 km di distanza.
"""
import pytest

from app.eccezioni import DatiNonValidiError
from app.servizi.saloni import RAGGIO_PREDEFINITO_KM, SaloniService, posizione_valida, raggio_valido

NAPOLI_CENTRO = ("40.8400", "14.2500")  # circa 2 km dal salone dei test


def _ids(risultati) -> list[int]:
    return [r.salone.id for r in risultati]


# --- Per regione e provincia ---

def test_regioni_e_province(conn):
    saloni = SaloniService(conn)
    assert len(saloni.regioni()) == 20 and "Campania" in saloni.regioni()
    assert {"NA", "SA", "CE", "AV", "BN"} == {p.sigla for p in saloni.province() if p.regione == "Campania"}


def test_cerca_per_regione_e_provincia(conn, salone_test, altro_salone_test):
    saloni = SaloniService(conn)
    in_campania = _ids(saloni.cerca_per_zona("Campania"))
    assert salone_test in in_campania and altro_salone_test not in in_campania
    assert salone_test in _ids(saloni.cerca_per_zona("Campania", "NA"))
    assert salone_test not in _ids(saloni.cerca_per_zona("Campania", "SA"))
    assert _ids(saloni.cerca_per_zona("Lazio", "RM")) == [altro_salone_test]


@pytest.mark.parametrize("regione, provincia", [
    ("Atlantide", ""),
    ("Campania", "RM"),       # provincia di un'altra regione
    ("Campania", "XX"),
    ("' OR 1=1 --", ""),
])
def test_zona_non_valida(conn, regione, provincia):
    with pytest.raises(DatiNonValidiError):
        SaloniService(conn).cerca_per_zona(regione, provincia)


def test_saloni_disattivati_non_trovati(conn, salone_test):
    with conn.cursor() as cur:
        cur.execute("UPDATE saloni SET attivo = FALSE WHERE id = %s", (salone_test,))
    assert salone_test not in _ids(SaloniService(conn).cerca_per_zona("Campania"))


# --- Vicino a una posizione ---

def test_cerca_vicino_con_distanza(conn, salone_test, altro_salone_test):
    risultati = SaloniService(conn).cerca_vicino(*NAPOLI_CENTRO, "5")
    assert _ids(risultati) == [salone_test]
    assert 1.5 < risultati[0].distanza_km < 2.5


def test_raggio_ampio_e_ordine_per_distanza(conn, salone_test, altro_salone_test):
    risultati = SaloniService(conn).cerca_vicino(*NAPOLI_CENTRO, "50")
    assert altro_salone_test not in _ids(risultati)  # Roma è a circa 190 km
    distanze = [r.distanza_km for r in risultati]
    assert distanze == sorted(distanze)


def test_ordine_per_nome(conn, salone_test):
    risultati = SaloniService(conn).cerca_vicino(*NAPOLI_CENTRO, "50", ordine="nome")
    nomi = [r.salone.nome for r in risultati]
    assert nomi == sorted(nomi, key=str.lower)


@pytest.mark.parametrize("lat, lon", [("", ""), ("abc", "14"), ("95", "14"), ("40", "200"), ("nan", "14"), ("inf", "14")])
def test_posizione_non_valida(lat, lon):
    with pytest.raises(DatiNonValidiError):
        posizione_valida(lat, lon)


def test_posizione_arrotondata_a_100_metri():
    assert posizione_valida("40.851812345", "14.268154321") == (40.852, 14.268)


@pytest.mark.parametrize("valore, km", [("5", 5), ("50", 50), ("250", RAGGIO_PREDEFINITO_KM), ("", RAGGIO_PREDEFINITO_KM)])
def test_raggio_valido(valore, km):
    assert raggio_valido(valore) == km


# --- Pagina ---

def test_pagina_di_ricerca(client, salone_test):
    assert client.get("/saloni").status_code == 200
    pagina = client.get("/saloni", query_string={"regione": "Campania", "provincia": "NA"})
    assert pagina.status_code == 200 and "Salone di prova dei test" in pagina.text
    vicino = client.get("/saloni", query_string={"lat": NAPOLI_CENTRO[0], "lon": NAPOLI_CENTRO[1], "raggio": "5"})
    assert "Salone di prova dei test" in vicino.text and "km" in vicino.text
    assert client.get("/saloni", query_string={"lat": "x", "lon": "y"}).status_code == 400
    assert client.get("/saloni", query_string={"regione": "Campania", "provincia": "RM"}).status_code == 400


def test_home_scelta_della_ricerca_sotto_le_card(client):
    pagina = client.get("/").text
    assert pagina.index('class="card-grandi"') < pagina.index('id="cerca"')
    sezione = pagina[pagina.index('id="cerca"'):]
    assert "data-usa-posizione" in sezione and 'href="/saloni"' in sezione
    assert "<form" not in sezione  # nella home si sceglie solo come cercare


def test_ricerca_mostra_solo_il_modulo_in_corso(client, salone_test):
    zona = client.get("/saloni").text
    assert 'id="cerca-zona"' in zona and 'id="cerca-vicino"' not in zona
    assert "data-usa-posizione" in zona  # per passare alla ricerca per posizione
    vicino = client.get("/saloni", query_string={"lat": NAPOLI_CENTRO[0], "lon": NAPOLI_CENTRO[1], "raggio": "25"}).text
    assert 'id="cerca-vicino"' in vicino and 'id="cerca-zona"' not in vicino
    assert 'name="lat" value="40.84"' in vicino and '<option value="25" selected>' in vicino
    assert "data-usa-posizione" not in vicino and 'href="/saloni"' in vicino


def test_posizione_non_valida_torna_alla_ricerca_per_zona(client):
    pagina = client.get("/saloni", query_string={"lat": "x", "lon": "y"})
    assert pagina.status_code == 400
    assert 'id="cerca-zona"' in pagina.text and 'id="cerca-vicino"' not in pagina.text


def test_avviso_solo_con_testo_fisso(client):
    pagina = client.get("/saloni", query_string={"avviso": "posizione"}).text
    assert "Non è stato possibile usare la tua posizione" in pagina and 'id="cerca-zona"' in pagina
    altro = client.get("/saloni", query_string={"avviso": "<script>alert(1)</script>"}).text
    assert "alert(1)" not in altro and 'class="avviso"' not in altro

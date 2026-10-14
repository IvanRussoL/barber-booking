from datetime import UTC, datetime, timedelta

from flask import Blueprint, render_template, request, url_for

from app.db import ottieni_connessione
from app.eccezioni import DatiNonValidiError
from app.servizi.disponibilita import DisponibilitaService
from app.servizi.recensioni import RecensioniService
from app.servizi.salone import SaloneService
from app.servizi.saloni import (ORDINI_VICINO, ORDINI_ZONA, RAGGI_KM, SaloniService, posizione_valida,
                                raggio_valido)

bp = Blueprint("pubblico", __name__)


def _punto_mappa(salone, con_link: bool = True) -> dict:
    """
    Un salone come lo legge la mappa (mappa.js): nome, indirizzo, coordinate e link alla sua pagina.
    """
    return {"nome": salone.nome, "indirizzo": salone.indirizzo, "lat": float(salone.latitudine),
            "lon": float(salone.longitudine),
            "url": url_for("pubblico.salone", salone_id=salone.id) if con_link else None}


def _dati_ricerca(saloni: SaloniService) -> dict:
    """
    Variabili per i moduli di ricerca (_ricerca.html): regioni, province, raggi e ordinamenti.
    """
    return {"regioni": saloni.regioni(), "province": saloni.province(), "raggi": RAGGI_KM,
            "ordini_vicino": ORDINI_VICINO, "ordini_zona": ORDINI_ZONA}


@bp.route("/")
def home():
    """
    Pagina iniziale della piattaforma: carosello e moduli per trovare un salone.
    """
    return render_template("pubblico/home.html", dati={}, **_dati_ricerca(SaloniService(ottieni_connessione())))


@bp.route("/saloni")
def ricerca():
    """
    Ricerca dei saloni: vicino al cliente (lat e lon inviate dal browser, con il raggio scelto)
    oppure per regione e provincia. La posizione non viene salvata.
    """
    saloni = SaloniService(ottieni_connessione())
    parametri = request.args
    risultati, modo, zona, errore, dati_mappa = None, None, None, None, None
    try:
        if parametri.get("lat") or parametri.get("lon"):
            modo = "vicino"
            risultati = saloni.cerca_vicino(parametri.get("lat", ""), parametri.get("lon", ""),
                                            parametri.get("raggio", ""), parametri.get("ordine", ""))
        elif parametri.get("regione"):
            modo = "zona"
            risultati = saloni.cerca_per_zona(parametri["regione"], parametri.get("provincia", ""),
                                              parametri.get("ordine", ""))
            sigla = parametri.get("provincia")
            zona = next((p.nome for p in saloni.province() if p.sigla == sigla), parametri["regione"])
    except DatiNonValidiError as eccezione:
        risultati, errore = None, str(eccezione)
    raggio = raggio_valido(parametri.get("raggio", ""))
    if risultati is not None and (risultati or modo == "vicino"):
        dati_mappa = {"saloni": [_punto_mappa(r.salone) for r in risultati], "tu": None}
        if modo == "vicino":  # la posizione già arrotondata, rimandata solo a questa pagina
            lat, lon = posizione_valida(parametri["lat"], parametri["lon"])
            dati_mappa["tu"] = {"lat": lat, "lon": lon, "raggio_km": raggio}
    return render_template(
        "pubblico/saloni.html", dati=parametri, risultati=risultati, modo=modo, zona=zona, errore=errore,
        raggio=raggio, dati_mappa=dati_mappa, **_dati_ricerca(saloni),
    ), 400 if errore else 200


@bp.route("/saloni/<int:salone_id>")
def salone(salone_id: int):
    """
    Pagina pubblica di un salone: stato di apertura in questo momento, orari, date particolari, contatti
    e ultime recensioni.
    Un salone inesistente o disattivato risulta non trovato (404).
    """
    connessione = ottieni_connessione()
    scelto = SaloniService(connessione).salone_pubblico(salone_id)
    disponibilita = DisponibilitaService(connessione, scelto.id)
    aperto, stato_apertura = disponibilita.stato_apertura(datetime.now(UTC))
    oggi = datetime.now(disponibilita.fuso_orario).date()
    media, numero, recensioni = RecensioniService(connessione).del_salone(scelto.id)
    return render_template(
        "pubblico/salone.html", salone=scelto, aperto=aperto, stato_apertura=stato_apertura,
        media_voti=media, numero_recensioni=numero, recensioni=recensioni,
        dati_mappa={"saloni": [_punto_mappa(scelto, con_link=False)], "tu": None},
        oggi=oggi.isoweekday(), orari=disponibilita.orario_settimanale(),
        speciali=disponibilita.giornate_speciali(oggi, oggi + timedelta(days=60)),
    )


@bp.route("/saloni/<int:salone_id>/servizi")
def servizi(salone_id: int):
    """
    Listino pubblico di un salone: solo i servizi attivi, con durata e prezzo.
    """
    connessione = ottieni_connessione()
    scelto = SaloniService(connessione).salone_pubblico(salone_id)
    elenco = SaloneService(connessione, scelto.id).elenca_servizi()
    return render_template("pubblico/servizi.html", salone=scelto, servizi=elenco)

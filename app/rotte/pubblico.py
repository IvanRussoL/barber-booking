from datetime import UTC, datetime, timedelta

from flask import Blueprint, render_template

from app.db import ottieni_connessione
from app.repository.impostazioni import ImpostazioniRepository
from app.servizi.disponibilita import DisponibilitaService
from app.servizi.salone import SaloneService

bp = Blueprint("pubblico", __name__)


@bp.route("/")
def home():
    """
    Pagina iniziale: stato di apertura in questo momento, accesso a prenotazione e listino, orari e contatti.
    """
    connessione = ottieni_connessione()
    disponibilita = DisponibilitaService(connessione)
    aperto, stato_apertura = disponibilita.stato_apertura(datetime.now(UTC))
    oggi = datetime.now(disponibilita.fuso_orario).date()
    return render_template(
        "pubblico/home.html", aperto=aperto, stato_apertura=stato_apertura, oggi=oggi.isoweekday(),
        orari=disponibilita.orario_settimanale(), impostazioni=ImpostazioniRepository(connessione).leggi(),
        speciali=disponibilita.giornate_speciali(oggi, oggi + timedelta(days=60)),
    )


@bp.route("/servizi")
def servizi():
    """
    Listino pubblico: solo i servizi attivi, con durata e prezzo.
    """
    elenco = SaloneService(ottieni_connessione()).elenca_servizi()
    return render_template("pubblico/servizi.html", servizi=elenco)

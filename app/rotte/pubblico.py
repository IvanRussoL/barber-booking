from flask import Blueprint, render_template

from app.db import ottieni_connessione
from app.servizi.salone import SaloneService

bp = Blueprint("pubblico", __name__)


@bp.route("/")
def home():
    """
    Pagina iniziale del sito.
    """
    return render_template("pubblico/home.html")


@bp.route("/servizi")
def servizi():
    """
    Listino pubblico: solo i servizi attivi, con durata e prezzo.
    """
    elenco = SaloneService(ottieni_connessione()).elenca_servizi()
    return render_template("pubblico/servizi.html", servizi=elenco)

import os

from flask import Flask, render_template
from app.db import chiudi_connessione
from app.eccezioni import BarberBookingError
from app.rotte import pubblico

def gestisci_errore(errore: BarberBookingError):
    """
    Mostra la pagina di errore con il messaggio dell'eccezione.
    Returns: la pagina errore.html con codice HTTP 400.
    """
    return render_template("errore.html", messaggio=str(errore)), 400


def create_app(config: dict | None = None) -> Flask:
    """
    Crea e configura l'applicazione Flask.
    Args: config, valori che sostituiscono quelli predefiniti (usato dai test).
    Returns: l'applicazione configurata.
    Raises: KeyError se SECRET_KEY manca dalle variabili d'ambiente.
    """

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ["SECRET_KEY"],
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    app.teardown_appcontext(chiudi_connessione)
    app.register_blueprint(pubblico.bp)
    app.register_error_handler(BarberBookingError, gestisci_errore)
    return app
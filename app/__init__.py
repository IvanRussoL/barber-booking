import os
from datetime import datetime

from flask import Flask, g, render_template, session
from flask_wtf.csrf import CSRFError, CSRFProtect

from app.comandi import crea_proprietario, crea_salone
from app.db import chiudi_connessione, ottieni_connessione
from app.eccezioni import BarberBookingError, RisorsaNonTrovataError
from app.formato import formatta_data_ora, formatta_durata, formatta_euro
from app.limiti import limiter
from app.pagamenti.finto import FakeProvider
from app.repository.salone import SaloneRepository
from app.repository.utente import UtenteRepository
from app.rotte import account, auth, cliente, dipendente, proprietario, pubblico

csrf = CSRFProtect()

MESSAGGI_HTTP = {
    403: "Non hai i permessi per aprire questa pagina.",
    404: "Pagina non trovata.",
    429: "Troppi tentativi sbagliati: aspetta un minuto e riprova.",
}


def gestisci_errore(errore: BarberBookingError):
    """
    Mostra la pagina di errore con il messaggio dell'eccezione.
    Returns: la pagina errore.html con codice HTTP 400.
    """
    return render_template("errore.html", messaggio=str(errore)), 400


def gestisci_non_trovato(errore: RisorsaNonTrovataError):
    """
    Dato inesistente o di un altro utente: stessa risposta in entrambi i casi, per non rivelare nulla.
    Returns: la pagina errore.html con codice HTTP 404.
    """
    return render_template("errore.html", messaggio=str(errore)), 404


def gestisci_errore_http(errore):
    """
    Mostra la pagina di errore in italiano per i codici 403, 404 e 429.
    Returns: la pagina errore.html con lo stesso codice dell'errore.
    """
    return render_template("errore.html", messaggio=MESSAGGI_HTTP[errore.code]), errore.code


def gestisci_errore_csrf(errore: CSRFError):
    """
    Modulo inviato senza token CSRF valido (es. pagina rimasta aperta troppo a lungo).
    Returns: la pagina errore.html con codice HTTP 400.
    """
    return render_template(
        "errore.html", messaggio="Modulo scaduto o non valido: ricarica la pagina e riprova."
    ), 400


def carica_utente() -> None:
    """
    Prima di ogni richiesta ricarica dal database l'utente della sessione e lo salva in g.utente.
    Un utente cancellato o disattivato viene fatto uscire subito.
    """
    g.utente = None
    utente_id = session.get("utente_id")
    if utente_id is None:
        return
    utente = UtenteRepository(ottieni_connessione()).leggi_per_id(utente_id)
    if utente is None or not utente.attivo:
        session.clear()
        return
    g.utente = utente


def dati_comuni() -> dict:
    """
    Dati comuni a tutte le pagine: l'anno per il piè di pagina; puo_prenotare, vero per visitatori
    e clienti, che decide se mostrare i pulsanti "Prenota"; il salone in cui lavora chi è loggato
    (None per visitatori e clienti), mostrato nell'intestazione dell'area di lavoro.
    Returns: dizionario con anno, puo_prenotare e salone_utente.
    """
    utente = g.get("utente")
    salone_utente = None
    if utente is not None and utente.salone_id is not None:
        salone_utente = SaloneRepository(ottieni_connessione()).leggi_per_id(utente.salone_id)
    return {
        "anno": datetime.now().year,
        "puo_prenotare": utente is None or utente.ruolo == "cliente",
        "salone_utente": salone_utente,
    }


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

    csrf.init_app(app)
    limiter.init_app(app)
    # Provider di pagamento usato dai servizi: per ora solo quello simulato.
    app.extensions["provider_pagamenti"] = app.config.get("PROVIDER_PAGAMENTI") or FakeProvider()
    app.before_request(carica_utente)
    app.teardown_appcontext(chiudi_connessione)

    app.register_blueprint(pubblico.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(cliente.bp)
    app.register_blueprint(dipendente.bp)
    app.register_blueprint(proprietario.bp)

    app.register_error_handler(BarberBookingError, gestisci_errore)
    app.register_error_handler(RisorsaNonTrovataError, gestisci_non_trovato)
    app.register_error_handler(CSRFError, gestisci_errore_csrf)
    for codice in MESSAGGI_HTTP:
        app.register_error_handler(codice, gestisci_errore_http)

    app.context_processor(dati_comuni)
    app.add_template_filter(formatta_euro, "euro")
    app.add_template_filter(formatta_durata, "durata")
    app.add_template_filter(formatta_data_ora, "data_ora")
    app.cli.add_command(crea_salone)
    app.cli.add_command(crea_proprietario)
    return app

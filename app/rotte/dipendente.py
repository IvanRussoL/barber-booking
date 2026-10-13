from flask import Blueprint, abort, current_app, g, render_template

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.servizi.prenotazione import PrenotazioneService

bp = Blueprint("dipendente", __name__, url_prefix="/dipendente")


@bp.before_request
def controlla_dipendente():
    """
    Nega per default: rotte riservate a chi riceve prenotazioni (dipendenti, e proprietario se lavora in sala).
    """
    risposta = controlla_accesso("dipendente", "proprietario")
    if risposta is None and not g.utente.riceve_prenotazioni:
        abort(403)
    return risposta


@bp.route("/")
def agenda():
    """
    Agenda personale: solo gli appuntamenti di chi è loggato, letti con il suo id di sessione.
    """
    servizio = PrenotazioneService(ottieni_connessione(), current_app.extensions["provider_pagamenti"])
    return render_template(
        "dipendente/agenda.html", appuntamenti=servizio.agenda(g.utente.id),
        fuso_orario=servizio.disponibilita.fuso_orario,
    )

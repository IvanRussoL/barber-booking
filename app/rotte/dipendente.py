from flask import Blueprint, abort, g, render_template

from app.accessi import controlla_accesso

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
    Agenda personale di chi riceve prenotazioni.
    """
    return render_template("dipendente/agenda.html")

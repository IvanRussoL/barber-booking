from flask import Blueprint, render_template

from app.accessi import controlla_accesso

bp = Blueprint("proprietario", __name__, url_prefix="/proprietario")


@bp.before_request
def controlla_proprietario():
    """
    Nega per default: ogni rotta di questo Blueprint è riservata al proprietario.
    """
    return controlla_accesso("proprietario")


@bp.route("/")
def pannello():
    """
    Pannello di gestione del salone.
    """
    return render_template("proprietario/pannello.html")

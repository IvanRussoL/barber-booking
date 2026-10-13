from flask import Blueprint, render_template

from app.accessi import controlla_accesso

bp = Blueprint("cliente", __name__, url_prefix="/cliente")


@bp.before_request
def controlla_cliente():
    """
    Nega per default: ogni rotta di questo Blueprint è riservata ai clienti.
    """
    return controlla_accesso("cliente")


@bp.route("/")
def area():
    """
    Area personale del cliente.
    """
    return render_template("cliente/area.html")

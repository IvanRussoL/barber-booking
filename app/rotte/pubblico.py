from flask import Blueprint

bp = Blueprint("pubblico", __name__)


@bp.route("/")
def home():
    """
    Pagina iniziale del sito.
    """
    return "Barber Booking"
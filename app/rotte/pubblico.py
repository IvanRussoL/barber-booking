from flask import Blueprint, render_template

bp = Blueprint("pubblico", __name__)


@bp.route("/")
def home():
    """
    Pagina iniziale del sito.
    """
    return render_template("pubblico/home.html")
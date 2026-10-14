from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.eccezioni import DatiNonValidiError
from app.limiti import LIMITE_TENTATIVI, limiter, tentativo_fallito
from app.rotte.auth import PAGINA_INIZIALE
from app.servizi.auth import AuthService

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.before_request
def controlla_utente():
    """
    Nega per default: le pagine dell'account sono per chiunque abbia fatto il login, di qualsiasi ruolo.
    """
    return controlla_accesso("cliente", "dipendente", "proprietario")


@bp.route("/", methods=["GET", "POST"])
@limiter.limit(LIMITE_TENTATIVI, methods=["POST"], deduct_when=tentativo_fallito)
def account():
    """
    Dati dell'account e cambio della password: serve quella attuale, così chi trova una sessione
    aperta non può cambiarla. Dopo 5 tentativi sbagliati in un minuto risponde 429.
    """
    if request.method == "GET":
        return render_template("account/account.html")
    try:
        AuthService(ottieni_connessione()).cambia_password(
            g.utente.id, request.form.get("attuale", ""), request.form.get("nuova", ""),
            request.form.get("conferma", ""),
        )
    except DatiNonValidiError as errore:
        return render_template("account/account.html", errore=str(errore)), 400
    flash("Password cambiata.")
    return redirect(url_for(PAGINA_INIZIALE[g.utente.ruolo]))

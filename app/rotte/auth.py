from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.db import ottieni_connessione
from app.eccezioni import CredenzialiNonValideError, DatiNonValidiError, EmailGiaRegistrataError
from app.limiti import LIMITE_TENTATIVI, limiter, tentativo_fallito
from app.servizi.auth import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")

PAGINA_INIZIALE = {
    "cliente": "cliente.area",
    "dipendente": "dipendente.agenda",
    "proprietario": "proprietario.pannello",
}


@bp.route("/registrazione", methods=["GET", "POST"])
def registrazione():
    """
    Modulo di registrazione dei clienti; in caso di errore lo mostra di nuovo con i dati inseriti.
    """
    if request.method == "GET":
        return render_template("auth/registrazione.html", dati={})
    try:
        AuthService(ottieni_connessione()).registra(
            request.form.get("email", ""),
            request.form.get("password", ""),
            request.form.get("nome", ""),
            request.form.get("cognome", ""),
            request.form.get("telefono", ""),
        )
    except (DatiNonValidiError, EmailGiaRegistrataError) as errore:
        return render_template(
            "auth/registrazione.html", errore=str(errore), dati=request.form
        ), 400
    flash("Registrazione completata: ora puoi accedere.")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(LIMITE_TENTATIVI, methods=["POST"], deduct_when=tentativo_fallito)
def login():
    """
    Login: svuota la sessione e vi salva solo l'id dell'utente, poi apre la pagina del suo ruolo.
    Dopo 5 tentativi sbagliati in un minuto dallo stesso indirizzo IP risponde 429.
    """
    if request.method == "GET":
        return render_template("auth/login.html", email="")
    email = request.form.get("email", "")
    try:
        utente = AuthService(ottieni_connessione()).autentica(email, request.form.get("password", ""))
    except CredenzialiNonValideError as errore:
        return render_template("auth/login.html", errore=str(errore), email=email), 400
    session.clear()
    session["utente_id"] = utente.id
    return redirect(url_for(PAGINA_INIZIALE[utente.ruolo]))


@bp.route("/logout", methods=["POST"])
def logout():
    """
    Logout: svuota la sessione. Solo POST, così un link su un altro sito non può far uscire l'utente.
    """
    session.clear()
    flash("Sei uscito dal tuo account.")
    return redirect(url_for("pubblico.home"))

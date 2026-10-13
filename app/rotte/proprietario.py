from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.eccezioni import DatiNonValidiError, ServizioGiaEsistenteError
from app.servizi.salone import SaloneService

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


# --- Servizi ---

@bp.route("/servizi")
def servizi():
    """
    Elenco di tutti i servizi, compresi quelli disattivati.
    """
    elenco = SaloneService(ottieni_connessione()).elenca_servizi(solo_attivi=False)
    return render_template("proprietario/servizi.html", servizi=elenco)


@bp.route("/servizi/nuovo", methods=["GET", "POST"])
def nuovo_servizio():
    """
    Modulo di creazione di un servizio; in caso di errore lo mostra di nuovo con i dati inseriti.
    """
    if request.method == "GET":
        return render_template("proprietario/servizio_modulo.html", dati={}, servizio_id=None)
    try:
        SaloneService(ottieni_connessione()).crea_servizio(
            request.form.get("nome", ""),
            request.form.get("descrizione", ""),
            request.form.get("durata_minuti", ""),
            request.form.get("prezzo_euro", ""),
        )
    except (DatiNonValidiError, ServizioGiaEsistenteError) as errore:
        return render_template(
            "proprietario/servizio_modulo.html", errore=str(errore), dati=request.form, servizio_id=None
        ), 400
    flash("Servizio creato.")
    return redirect(url_for("proprietario.servizi"))


@bp.route("/servizi/<int:servizio_id>/modifica", methods=["GET", "POST"])
def modifica_servizio(servizio_id: int):
    """
    Modulo di modifica di un servizio, precompilato con i valori attuali.
    Un id inesistente arriva al gestore di RisorsaNonTrovataError (404).
    """
    salone = SaloneService(ottieni_connessione())
    if request.method == "GET":
        servizio = salone.leggi_servizio(servizio_id)
        dati = {
            "nome": servizio.nome,
            "descrizione": servizio.descrizione or "",
            "durata_minuti": servizio.durata_minuti,
            "prezzo_euro": f"{servizio.prezzo_centesimi // 100},{servizio.prezzo_centesimi % 100:02d}",
        }
        return render_template("proprietario/servizio_modulo.html", dati=dati, servizio_id=servizio_id)
    try:
        salone.modifica_servizio(
            servizio_id,
            request.form.get("nome", ""),
            request.form.get("descrizione", ""),
            request.form.get("durata_minuti", ""),
            request.form.get("prezzo_euro", ""),
        )
    except (DatiNonValidiError, ServizioGiaEsistenteError) as errore:
        return render_template(
            "proprietario/servizio_modulo.html", errore=str(errore), dati=request.form,
            servizio_id=servizio_id,
        ), 400
    flash("Servizio modificato.")
    return redirect(url_for("proprietario.servizi"))


@bp.route("/servizi/<int:servizio_id>/attivo", methods=["POST"])
def imposta_attivo_servizio(servizio_id: int):
    """
    Disattiva o riattiva un servizio: il modulo invia attivo = "1" oppure "0".
    """
    attivo = request.form.get("attivo") == "1"
    SaloneService(ottieni_connessione()).imposta_attivo(servizio_id, attivo)
    flash("Servizio riattivato." if attivo else "Servizio disattivato: non è più prenotabile.")
    return redirect(url_for("proprietario.servizi"))

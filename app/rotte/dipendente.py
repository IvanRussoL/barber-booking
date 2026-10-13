from flask import Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, url_for

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.eccezioni import AnnullamentoNonConsentitoError
from app.formato import formatta_euro
from app.servizi.prenotazione import PrenotazioneService
from app.servizi.statistiche import StatisticheService, periodo_valido

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


def _prenotazioni() -> PrenotazioneService:
    """
    PrenotazioneService con la connessione della richiesta e il provider di pagamento dell'app.
    """
    return PrenotazioneService(ottieni_connessione(), current_app.extensions["provider_pagamenti"])


@bp.route("/")
def agenda():
    """
    Agenda personale: prossimi appuntamenti e storico (passati e annullati) di chi è loggato,
    letti con il suo id di sessione.
    """
    servizio = _prenotazioni()
    return render_template(
        "dipendente/agenda.html", appuntamenti=servizio.agenda(g.utente.id),
        storico=servizio.storico_professionista(g.utente.id), fuso_orario=servizio.disponibilita.fuso_orario,
    )


@bp.route("/prenotazioni/<int:prenotazione_id>/annulla", methods=["GET", "POST"])
def annulla_prenotazione(prenotazione_id: int):
    """
    Annullamento di un appuntamento della propria agenda, con rimborso al cliente.
    Un appuntamento di un altro professionista risulta non trovato (404).
    """
    servizio = _prenotazioni()
    appuntamento = servizio.prenotazione_per_il_salone(prenotazione_id, g.utente)
    if request.method == "GET":
        return render_template(
            "annulla_salone.html", appuntamento=appuntamento, fuso_orario=servizio.disponibilita.fuso_orario,
            torna_a=url_for("dipendente.agenda"),
        )
    try:
        rimborsato = servizio.annulla_dal_salone(prenotazione_id, g.utente)
    except AnnullamentoNonConsentitoError as errore:
        flash(str(errore))
    else:
        flash(f"Appuntamento annullato. Il cliente riceve un rimborso di {formatta_euro(rimborsato)}.")
    return redirect(url_for("dipendente.agenda"))


@bp.route("/statistiche")
def statistiche():
    """
    Statistiche personali: solo le prenotazioni di chi è loggato (id dalla sessione, mai dall'URL).
    """
    giorni = periodo_valido(request.args.get("giorni"))
    riepilogo = StatisticheService(ottieni_connessione()).riepilogo(giorni, dipendente_id=g.utente.id)
    return render_template("dipendente/statistiche.html", giorni=giorni, riepilogo=riepilogo)


@bp.route("/statistiche/andamento.png")
def grafico_andamento():
    """
    Grafico delle proprie prenotazioni per settimana, generato in memoria.
    """
    giorni = periodo_valido(request.args.get("giorni"))
    immagine = StatisticheService(ottieni_connessione()).grafico_andamento(giorni, dipendente_id=g.utente.id)
    return Response(immagine, mimetype="image/png", headers={"Cache-Control": "no-store"})


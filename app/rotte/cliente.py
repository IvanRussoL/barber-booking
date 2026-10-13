from datetime import UTC, date, datetime

from flask import (Blueprint, current_app, flash, g, jsonify, redirect, render_template,
                   request, url_for)

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.eccezioni import AnnullamentoNonConsentitoError, DatiNonValidiError, SlotNonDisponibileError
from app.formato import formatta_euro
from app.repository.impostazioni import ImpostazioniRepository
from app.repository.utente import UtenteRepository
from app.servizi.prenotazione import PrenotazioneService
from app.servizi.salone import SaloneService

bp = Blueprint("cliente", __name__, url_prefix="/cliente")


def _prenotazioni() -> PrenotazioneService:
    """
    PrenotazioneService con la connessione della richiesta e il provider di pagamento dell'app.
    """
    return PrenotazioneService(ottieni_connessione(), current_app.extensions["provider_pagamenti"])


@bp.before_request
def controlla_cliente():
    """
    Nega per default: ogni rotta di questo Blueprint è riservata ai clienti.
    """
    return controlla_accesso("cliente")


@bp.route("/")
def area():
    """
    Area personale: storico delle prenotazioni del cliente e totale speso.
    L'id del cliente viene dalla sessione (g.utente), mai dall'URL.
    """
    servizio = _prenotazioni()
    storico = servizio.storico_cliente(g.utente.id)
    return render_template(
        "cliente/area.html", storico=storico, totale_speso=sum(r.pagato_centesimi for r in storico),
        fuso_orario=servizio.disponibilita.fuso_orario,
    )


@bp.route("/prenotazioni/<int:prenotazione_id>/annulla", methods=["GET", "POST"])
def annulla_prenotazione(prenotazione_id: int):
    """
    GET: pagina di conferma. POST: annullamento con rimborso.
    Una prenotazione di un altro cliente risulta non trovata (404), come una inesistente.
    """
    servizio = _prenotazioni()
    prenotazione = servizio.prenotazione_del_cliente(prenotazione_id, g.utente.id)
    if request.method == "GET":
        return render_template(
            "cliente/annulla.html", prenotazione=prenotazione, fuso_orario=servizio.disponibilita.fuso_orario,
        )
    try:
        rimborsato = servizio.annulla_dal_cliente(prenotazione_id, g.utente.id)
    except AnnullamentoNonConsentitoError as errore:
        flash(str(errore))
        return redirect(url_for("cliente.area"))
    flash(f"Prenotazione annullata. Rimborso di {formatta_euro(rimborsato)}.")
    return redirect(url_for("cliente.area"))


# --- Prenotazione ---

def _pagina_prenotazione(dati, servizi_scelti: list[str], errore: str | None = None, codice: int = 200):
    """
    Mostra il modulo di prenotazione con servizi, professionisti, finestra di date e scelte già fatte.
    """
    connessione = ottieni_connessione()
    primo, ultimo = _prenotazioni().disponibilita.finestra(datetime.now(UTC))
    return render_template(
        "cliente/prenota.html",
        servizi=SaloneService(connessione).elenca_servizi(),
        professionisti=UtenteRepository(connessione).elenca_professionisti(),
        percentuale_acconto=ImpostazioniRepository(connessione).leggi().percentuale_acconto,
        primo_giorno=primo.isoformat(),
        ultimo_giorno=ultimo.isoformat(),
        dati=dati,
        servizi_scelti=servizi_scelti,
        errore=errore,
    ), codice


@bp.route("/prenota", methods=["GET", "POST"])
def prenota():
    """
    Modulo di prenotazione. Il POST crea la prenotazione in attesa di pagamento
    e porta alla pagina di pagamento del provider.
    """
    if request.method == "GET":
        return _pagina_prenotazione({}, [])
    try:
        _, url_pagamento = _prenotazioni().crea(
            g.utente,
            request.form.get("dipendente_id", ""),
            request.form.getlist("servizi"),
            request.form.get("data", ""),
            request.form.get("ora", ""),
            request.form.get("modalita", ""),
        )
    except (DatiNonValidiError, SlotNonDisponibileError) as errore:
        ottieni_connessione().rollback()  # libera subito il blocco sul dipendente
        return _pagina_prenotazione(request.form, request.form.getlist("servizi"), str(errore), 400)
    return redirect(url_pagamento)


@bp.route("/slot")
def slot():
    """
    Orari liberi in formato JSON, chiesti con fetch dalla pagina di prenotazione.
    Parametri: dipendente_id, data (AAAA-MM-GG) e uno o più servizi.
    """
    servizio = _prenotazioni()
    try:
        liberi = servizio.slot_per_scelta(
            request.args.get("dipendente_id", ""),
            request.args.getlist("servizi"),
            request.args.get("data", ""),
            cliente_id=g.utente.id,
        )
    except DatiNonValidiError as errore:
        return jsonify(errore=str(errore)), 400
    # Qui la data è già stata controllata da slot_per_scelta.
    incerta = servizio.disponibilita.da_definire(date.fromisoformat(request.args["data"]))
    return jsonify(slot=[inizio.strftime("%H:%M") for inizio in liberi], da_definire=incerta)


# --- Pagamento simulato (FakeProvider) ---

@bp.route("/pagamento/<riferimento>")
def pagamento(riferimento: str):
    """
    Pagina di pagamento simulata: con Stripe il cliente andrebbe sulla pagina di Stripe Checkout.
    """
    servizio = _prenotazioni()
    movimento, prenotazione = servizio.pagamento_del_cliente(riferimento, g.utente.id)
    dipendente = UtenteRepository(ottieni_connessione()).leggi_per_id(prenotazione.dipendente_id)
    return render_template(
        "cliente/pagamento.html", pagamento=movimento, prenotazione=prenotazione,
        dipendente=dipendente, fuso_orario=servizio.disponibilita.fuso_orario,
    )


@bp.route("/pagamento/<riferimento>/paga", methods=["POST"])
def paga(riferimento: str):
    """
    Simula il pagamento riuscito e la notifica del provider che conferma la prenotazione.
    """
    servizio = _prenotazioni()
    servizio.pagamento_del_cliente(riferimento, g.utente.id)
    if servizio.conferma_pagamento(riferimento):
        flash("Pagamento riuscito: prenotazione confermata.")
    else:
        flash("Il tempo per pagare era scaduto: il pagamento è stato rimborsato.")
    return redirect(url_for("cliente.area"))


@bp.route("/pagamento/<riferimento>/annulla", methods=["POST"])
def annulla_pagamento(riferimento: str):
    """
    Il cliente esce dal pagamento: la prenotazione in attesa viene annullata e lo slot torna libero.
    """
    servizio = _prenotazioni()
    servizio.pagamento_del_cliente(riferimento, g.utente.id)
    servizio.annulla_pagamento(riferimento)
    flash("Pagamento annullato: la prenotazione non è stata registrata.")
    return redirect(url_for("cliente.prenota"))

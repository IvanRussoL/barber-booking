from datetime import UTC, date, datetime

from flask import (Blueprint, current_app, flash, g, jsonify, redirect, render_template,
                   request, url_for)

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.eccezioni import (AnnullamentoNonConsentitoError, DatiNonValidiError, PagamentoNonDisponibileError,
                           RecensioneNonConsentitaError, RisorsaNonTrovataError, SlotNonDisponibileError)
from app.formato import formatta_euro
from app.pagamenti.finto import FakeProvider
from app.repository.utente import UtenteRepository
from app.servizi.prenotazione import PrenotazioneService
from app.servizi.recensioni import LUNGHEZZA_MASSIMA_COMMENTO, RecensioniService
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
    Area personale: storico delle prenotazioni del cliente in tutti i saloni e totale speso.
    L'id del cliente viene dalla sessione (g.utente), mai dall'URL.
    """
    storico = _prenotazioni().storico_cliente(g.utente.id)
    return render_template(
        "cliente/area.html", storico=storico, totale_speso=sum(r.pagato_centesimi for r in storico),
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
        disponibilita = servizio.disponibilita(prenotazione.salone_id)
        return render_template(
            "cliente/annulla.html", prenotazione=prenotazione, salone=disponibilita.salone,
            fuso_orario=disponibilita.fuso_orario,
        )
    try:
        rimborsato = servizio.annulla_dal_cliente(prenotazione_id, g.utente.id)
    except AnnullamentoNonConsentitoError as errore:
        flash(str(errore))
        return redirect(url_for("cliente.area"))
    flash(f"Prenotazione annullata. Rimborso di {formatta_euro(rimborsato)}.")
    return redirect(url_for("cliente.area"))


@bp.route("/prenotazioni/<int:prenotazione_id>/recensione", methods=["GET", "POST"])
def recensione(prenotazione_id: int):
    """
    Recensione di un appuntamento svolto. Una prenotazione di un altro cliente risulta non trovata (404);
    una non ancora svolta o già recensita riporta all'area personale con un messaggio.
    """
    recensioni = RecensioniService(ottieni_connessione())
    try:
        prenotazione = recensioni.prenotazione_da_recensire(prenotazione_id, g.utente.id)
    except RecensioneNonConsentitaError as errore:
        flash(str(errore))
        return redirect(url_for("cliente.area"))
    disponibilita = _prenotazioni().disponibilita(prenotazione.salone_id)
    pagina = {"prenotazione": prenotazione, "salone": disponibilita.salone, "fuso_orario": disponibilita.fuso_orario,
              "lunghezza_massima": LUNGHEZZA_MASSIMA_COMMENTO}
    if request.method == "GET":
        return render_template("cliente/recensione.html", dati={}, **pagina)
    try:
        recensioni.crea(prenotazione_id, g.utente.id, request.form.get("voto", ""), request.form.get("commento", ""))
    except DatiNonValidiError as errore:
        ottieni_connessione().rollback()  # libera il blocco sulla prenotazione
        return render_template("cliente/recensione.html", dati=request.form, errore=str(errore), **pagina), 400
    except RecensioneNonConsentitaError as errore:
        flash(str(errore))
        return redirect(url_for("cliente.area"))
    flash("Grazie: la tua recensione è pubblicata.")
    return redirect(url_for("cliente.area"))


# --- Prenotazione in un salone ---

def _pagina_prenotazione(salone_id: int, dati, servizi_scelti: list[str], errore: str | None = None,
                         codice: int = 200):
    """
    Mostra il modulo di prenotazione del salone con servizi, professionisti, finestra di date e scelte già fatte.
    Raises: RisorsaNonTrovataError se il salone non esiste o è disattivato (404).
    """
    connessione = ottieni_connessione()
    servizio = _prenotazioni()
    salone = servizio.salone_prenotabile(salone_id)
    primo, ultimo = servizio.disponibilita(salone.id).finestra(datetime.now(UTC))
    return render_template(
        "cliente/prenota.html",
        salone=salone,
        servizi=SaloneService(connessione, salone.id).elenca_servizi(),
        professionisti=UtenteRepository(connessione).elenca_professionisti(salone.id),
        primo_giorno=primo.isoformat(),
        ultimo_giorno=ultimo.isoformat(),
        dati=dati,
        servizi_scelti=servizi_scelti,
        errore=errore,
    ), codice


@bp.route("/saloni/<int:salone_id>/prenota", methods=["GET", "POST"])
def prenota(salone_id: int):
    """
    Modulo di prenotazione di un salone. Il POST crea la prenotazione in attesa di pagamento
    e porta alla pagina di pagamento del provider. Servizi e professionista devono essere di questo salone.
    """
    if request.method == "GET":
        return _pagina_prenotazione(salone_id, {}, [])
    try:
        _, url_pagamento = _prenotazioni().crea(
            g.utente,
            salone_id,
            request.form.get("dipendente_id", ""),
            request.form.getlist("servizi"),
            request.form.get("data", ""),
            request.form.get("ora", ""),
            request.form.get("modalita", ""),
        )
    except (DatiNonValidiError, SlotNonDisponibileError, PagamentoNonDisponibileError) as errore:
        ottieni_connessione().rollback()  # libera subito il blocco sul dipendente
        return _pagina_prenotazione(salone_id, request.form, request.form.getlist("servizi"), str(errore), 400)
    return redirect(url_pagamento)


@bp.route("/saloni/<int:salone_id>/slot")
def slot(salone_id: int):
    """
    Orari liberi in formato JSON, chiesti con fetch dalla pagina di prenotazione del salone.
    Parametri: dipendente_id, data (AAAA-MM-GG) e uno o più servizi.
    """
    servizio = _prenotazioni()
    try:
        liberi = servizio.slot_per_scelta(
            salone_id,
            request.args.get("dipendente_id", ""),
            request.args.getlist("servizi"),
            request.args.get("data", ""),
            cliente_id=g.utente.id,
        )
    except RisorsaNonTrovataError as errore:
        return jsonify(errore=str(errore)), 404
    except DatiNonValidiError as errore:
        return jsonify(errore=str(errore)), 400
    # Qui la data è già stata controllata da slot_per_scelta.
    incerta = servizio.disponibilita(salone_id).da_definire(date.fromisoformat(request.args["data"]))
    return jsonify(slot=[inizio.strftime("%H:%M") for inizio in liberi], da_definire=incerta)


# --- Ritorno da Stripe Checkout ---

@bp.route("/prenotazioni/<int:prenotazione_id>/pagamento-eseguito")
def pagamento_eseguito(prenotazione_id: int):
    """
    Pagina a cui Stripe riporta il cliente dopo il pagamento. Non conferma niente: la conferma
    arriva solo dal webhook firmato, perché questo indirizzo lo può aprire chiunque.
    """
    _, prenotazione = _prenotazioni().pagamento_in_attesa(prenotazione_id, g.utente.id)
    if prenotazione.stato == "confermata":
        flash("Pagamento riuscito: prenotazione confermata.")
    else:
        flash("Pagamento ricevuto: la prenotazione risulterà confermata appena Stripe ce lo comunica, di solito in pochi secondi.")
    return redirect(url_for("cliente.area"))


@bp.route("/prenotazioni/<int:prenotazione_id>/pagamento-annullato")
def pagamento_annullato(prenotazione_id: int):
    """
    Pagina a cui Stripe riporta il cliente se torna indietro senza pagare: può annullare subito la
    prenotazione (con un POST) e liberare l'orario; altrimenti l'orario si libera da solo alla scadenza.
    """
    servizio = _prenotazioni()
    pagamento_aperto, prenotazione = servizio.pagamento_in_attesa(prenotazione_id, g.utente.id)
    return render_template(
        "cliente/pagamento_annullato.html", pagamento=pagamento_aperto, prenotazione=prenotazione,
        fuso_orario=servizio.disponibilita(prenotazione.salone_id).fuso_orario,
    )


# --- Pagamento simulato (FakeProvider) ---

def _solo_pagamento_simulato() -> None:
    """
    Le pagine del pagamento simulato esistono solo con FakeProvider: con Stripe attivo, "Paga"
    confermerebbe una prenotazione senza un vero pagamento.
    Raises: RisorsaNonTrovataError (404) se il provider non è quello simulato.
    """
    if not isinstance(current_app.extensions["provider_pagamenti"], FakeProvider):
        raise RisorsaNonTrovataError("Pagina non trovata.")


@bp.route("/pagamento/<riferimento>")
def pagamento(riferimento: str):
    """
    Pagina di pagamento simulata: con Stripe il cliente va sulla pagina di Stripe Checkout.
    """
    _solo_pagamento_simulato()
    servizio = _prenotazioni()
    movimento, prenotazione = servizio.pagamento_del_cliente(riferimento, g.utente.id)
    dipendente = UtenteRepository(ottieni_connessione()).leggi_per_id(prenotazione.dipendente_id)
    disponibilita = servizio.disponibilita(prenotazione.salone_id)
    return render_template(
        "cliente/pagamento.html", pagamento=movimento, prenotazione=prenotazione, salone=disponibilita.salone,
        dipendente=dipendente, fuso_orario=disponibilita.fuso_orario,
    )


@bp.route("/pagamento/<riferimento>/paga", methods=["POST"])
def paga(riferimento: str):
    """
    Simula il pagamento riuscito e la notifica del provider che conferma la prenotazione.
    """
    _solo_pagamento_simulato()
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
    Il cliente esce dal pagamento: la prenotazione in attesa viene annullata e lo slot torna libero
    (con Stripe la sessione viene fatta scadere, così non si può più pagare).
    """
    servizio = _prenotazioni()
    _, prenotazione = servizio.pagamento_del_cliente(riferimento, g.utente.id)
    servizio.annulla_pagamento(riferimento)
    flash("Pagamento annullato: la prenotazione non è stata registrata.")
    return redirect(url_for("cliente.prenota", salone_id=prenotazione.salone_id))

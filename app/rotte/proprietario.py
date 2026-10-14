from datetime import datetime, timedelta

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request,
                   url_for)

from app.accessi import controlla_accesso
from app.db import ottieni_connessione
from app.eccezioni import AnnullamentoNonConsentitoError, DatiNonValidiError, ServizioGiaEsistenteError
from app.formato import formatta_euro
from app.repository.utente import UtenteRepository
from app.servizi.calendario import CalendarioService
from app.servizi.prenotazione import PrenotazioneService
from app.servizi.salone import SaloneService
from app.servizi.statistiche import StatisticheService, periodo_valido

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
    elenco = SaloneService(ottieni_connessione(), g.utente.salone_id).elenca_servizi(solo_attivi=False)
    return render_template("proprietario/servizi.html", servizi=elenco)


@bp.route("/servizi/nuovo", methods=["GET", "POST"])
def nuovo_servizio():
    """
    Modulo di creazione di un servizio; in caso di errore lo mostra di nuovo con i dati inseriti.
    """
    if request.method == "GET":
        return render_template("proprietario/servizio_modulo.html", dati={}, servizio_id=None)
    try:
        SaloneService(ottieni_connessione(), g.utente.salone_id).crea_servizio(
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
    salone = SaloneService(ottieni_connessione(), g.utente.salone_id)
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
    SaloneService(ottieni_connessione(), g.utente.salone_id).imposta_attivo(servizio_id, attivo)
    flash("Servizio riattivato." if attivo else "Servizio disattivato: non è più prenotabile.")
    return redirect(url_for("proprietario.servizi"))


# --- Statistiche ---

@bp.route("/statistiche")
def statistiche():
    """
    Statistiche del salone nel periodo scelto (7, 30 o 365 giorni): numeri principali e grafici.
    """
    giorni = periodo_valido(request.args.get("giorni"))
    servizio = StatisticheService(ottieni_connessione(), g.utente.salone_id)
    return render_template(
        "proprietario/statistiche.html", giorni=giorni, riepilogo=servizio.riepilogo(giorni),
        professionisti=servizio.per_professionista(giorni).to_dict("records"),
    )


@bp.route("/statistiche/<nome>.png")
def grafico(nome: str):
    """
    Immagine di un grafico, generata in memoria. Sta dietro il controllo del Blueprint come le pagine:
    i dati del salone non finiscono mai in una cartella pubblica.
    """
    giorni = periodo_valido(request.args.get("giorni"))
    servizio = StatisticheService(ottieni_connessione(), g.utente.salone_id)
    grafici = {
        "professionisti": servizio.grafico_professionisti,
        "fasce": servizio.grafico_fasce,
        "andamento": servizio.grafico_andamento,
    }
    if nome not in grafici:
        abort(404)
    return Response(grafici[nome](giorni), mimetype="image/png", headers={"Cache-Control": "no-store"})


# --- Dipendenti e loro agende ---

def _prenotazioni() -> PrenotazioneService:
    """
    PrenotazioneService con la connessione della richiesta e il provider di pagamento dell'app.
    """
    return PrenotazioneService(ottieni_connessione(), current_app.extensions["provider_pagamenti"])


@bp.route("/dipendenti")
def dipendenti():
    """
    Tutti i professionisti (compreso il proprietario se lavora in sala) con recapiti, appuntamenti futuri
    e lavoro svolto nel periodo, più il totale del salone.
    """
    giorni = periodo_valido(request.args.get("giorni"))
    connessione = ottieni_connessione()
    statistiche = StatisticheService(connessione, g.utente.salone_id)
    lavoro = {riga["dipendente_id"]: riga for riga in statistiche.per_professionista(giorni).to_dict("records")}
    prenotazioni = _prenotazioni()
    righe = [
        {"utente": utente, "prossimi": len(prenotazioni.agenda(utente.id)),
         "prenotazioni": lavoro.get(utente.id, {}).get("prenotazioni", 0),
         "valore_centesimi": lavoro.get(utente.id, {}).get("valore_centesimi", 0)}
        for utente in UtenteRepository(connessione).elenca_professionisti(g.utente.salone_id)
    ]
    return render_template(
        "proprietario/dipendenti.html", giorni=giorni, righe=righe, riepilogo=statistiche.riepilogo(giorni),
    )


@bp.route("/dipendenti/<int:dipendente_id>")
def agenda_dipendente(dipendente_id: int):
    """
    Agenda e storico di un professionista, visti dal proprietario, con la possibilità di annullare.
    Un professionista di un altro salone risulta non trovato (404), come uno inesistente.
    """
    professionista = UtenteRepository(ottieni_connessione()).leggi_per_id(dipendente_id)
    if (professionista is None or professionista.salone_id != g.utente.salone_id
            or not professionista.riceve_prenotazioni):
        abort(404)
    servizio = _prenotazioni()
    return render_template(
        "proprietario/agenda_dipendente.html", professionista=professionista,
        appuntamenti=servizio.agenda(dipendente_id), storico=servizio.storico_professionista(dipendente_id),
        fuso_orario=servizio.disponibilita(g.utente.salone_id).fuso_orario,
    )


@bp.route("/prenotazioni/<int:prenotazione_id>/annulla", methods=["GET", "POST"])
def annulla_prenotazione(prenotazione_id: int):
    """
    Annullamento per conto del salone di qualsiasi prenotazione confermata, con rimborso al cliente.
    """
    servizio = _prenotazioni()
    appuntamento = servizio.prenotazione_per_il_salone(prenotazione_id, g.utente)
    torna_a = url_for("proprietario.agenda_dipendente", dipendente_id=appuntamento.prenotazione.dipendente_id)
    if request.method == "GET":
        return render_template(
            "annulla_salone.html", appuntamento=appuntamento,
            fuso_orario=servizio.disponibilita(g.utente.salone_id).fuso_orario, torna_a=torna_a,
        )
    try:
        rimborsato = servizio.annulla_dal_salone(prenotazione_id, g.utente)
    except AnnullamentoNonConsentitoError as errore:
        flash(str(errore))
    else:
        flash(f"Prenotazione annullata. Il cliente riceve un rimborso di {formatta_euro(rimborsato)}.")
    return redirect(torna_a)


# --- Orari delle singole date ---

@bp.route("/orari")
def orari():
    """
    Calendario settimanale (sola lettura) e date speciali dei prossimi 12 mesi: festività da definire,
    chiusure e aperture decise dal proprietario.
    """
    calendario = CalendarioService(ottieni_connessione(), g.utente.salone_id)
    oggi = datetime.now(calendario.disponibilita.fuso_orario).date()
    return render_template(
        "proprietario/orari.html", settimana=calendario.disponibilita.orario_settimanale(),
        speciali=calendario.disponibilita.giornate_speciali(oggi, oggi + timedelta(days=365)),
    )


@bp.route("/orari/data", methods=["GET", "POST"])
def orari_data():
    """
    Modulo per decidere l'orario di una data: aperto con uno o due turni, oppure chiuso.
    La data arriva nell'URL (?data=AAAA-MM-GG) o nel modulo.
    """
    calendario = CalendarioService(ottieni_connessione(), g.utente.salone_id)
    disponibilita = calendario.disponibilita
    if request.method == "POST":
        try:
            giorno = calendario.imposta_eccezione(
                request.form.get("data", ""), request.form.get("aperto", ""),
                [(request.form.get("inizio_1", ""), request.form.get("fine_1", "")),
                 (request.form.get("inizio_2", ""), request.form.get("fine_2", ""))],
                request.form.get("nota", ""),
            )
        except DatiNonValidiError as errore:
            return render_template("proprietario/orari_data.html", dati=request.form, errore=str(errore)), 400
        flash(f"Orari del {giorno:%d/%m/%Y} salvati.")
        return redirect(url_for("proprietario.orari"))

    try:
        giorno = datetime.strptime(request.args.get("data", ""), "%Y-%m-%d").date()
    except ValueError:
        flash("Scegli una data valida.")
        return redirect(url_for("proprietario.orari"))
    turni = disponibilita.turni_del_giorno(giorno)
    eccezione = next(iter(disponibilita.giornate_speciali(giorno, giorno)), None)
    dati = {
        "data": giorno.isoformat(),
        "aperto": "no" if eccezione and eccezione.stato == "chiuso" else "si",
        "nota": (eccezione.nota if eccezione else "") or "",
    }
    for numero, turno in enumerate(turni[:2], start=1):
        dati[f"inizio_{numero}"] = turno.ora_inizio.strftime("%H:%M")
        dati[f"fine_{numero}"] = turno.ora_fine.strftime("%H:%M")
    return render_template("proprietario/orari_data.html", dati=dati, eccezione=eccezione)


@bp.route("/orari/ripristina", methods=["POST"])
def orari_ripristina():
    """
    Toglie l'eccezione di una data: torna l'orario settimanale (una festività torna "da definire").
    """
    try:
        giorno = CalendarioService(ottieni_connessione(), g.utente.salone_id).rimuovi_eccezione(request.form.get("data", ""))
    except DatiNonValidiError as errore:
        flash(str(errore))
    else:
        flash(f"Il {giorno:%d/%m/%Y} torna all'orario settimanale.")
    return redirect(url_for("proprietario.orari"))


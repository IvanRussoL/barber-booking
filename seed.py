"""
Dati di prova per la demo: servizi, due dipendenti, clienti, alcune prenotazioni future confermate
e uno storico di 4 mesi di prenotazioni pagate per le statistiche.
Si esegue dopo schema.sql e dopo flask crea-proprietario:  python seed.py
Si può rilanciare: salta ciò che esiste già. Le password dei profili di prova valgono solo in locale.
"""
import random
import secrets
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from app.db import crea_connessione
from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.pagamenti.finto import FakeProvider
from app.repository.impostazioni import ImpostazioniRepository
from app.repository.pagamento import PagamentoRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.servizio import ServizioRepository
from app.repository.statistiche import StatisticheRepository
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService
from app.servizi.disponibilita import DisponibilitaService, in_utc
from app.servizi.prenotazione import PrenotazioneService, calcola_acconto
from app.servizi.salone import SaloneService

PASSWORD_DEMO = "demo12345"

SERVIZI = [
    # nome, descrizione, durata in minuti, prezzo in euro
    ("Taglio", "Shampoo, taglio e asciugatura", "30", "18"),
    ("Barba", "Rifinitura con panno caldo", "30", "12"),
    ("Taglio e barba", "Il servizio completo", "60", "27"),
    ("Colore", "Colore e piega", "90", "45"),
    ("Piega", "Lavaggio e piega", "30", "15"),
]

DIPENDENTI = [
    ("marco@demo.it", "Marco", "Esposito", "+393331000001"),
    ("giulia@demo.it", "Giulia", "Russo", "+393331000002"),
]

CLIENTI = [
    ("anna@demo.it", "Anna", "Ferrara", "+393332000001"),
    ("luca@demo.it", "Luca", "De Rosa", "+393332000002"),
]

# Altri clienti, usati solo nello storico delle statistiche.
CLIENTI_STORICO = [
    ("sara@demo.it", "Sara", "Romano", "+393332000003"),
    ("paolo@demo.it", "Paolo", "Greco", "+393332000004"),
    ("chiara@demo.it", "Chiara", "Conti", "+393332000005"),
    ("giovanni@demo.it", "Giovanni", "Marino", "+393332000006"),
    ("elena@demo.it", "Elena", "Gallo", "+393332000007"),
]

GIORNI_STORICO = 120
PESO_SERVIZI = {"Taglio": 6, "Barba": 3, "Taglio e barba": 4, "Colore": 1, "Piega": 2}
ORE_DI_PUNTA = {10, 11, 17, 18, 19}


def crea_servizi(connessione) -> None:
    salone = SaloneService(connessione)
    for nome, descrizione, durata, prezzo in SERVIZI:
        esistente = ServizioRepository(connessione).leggi_per_nome(nome)
        if esistente is None:
            salone.crea_servizio(nome, descrizione, durata, prezzo)
            print(f"Servizio creato: {nome}")
        elif not esistente.attivo:
            salone.imposta_attivo(esistente.id, True)  # servono attivi per le prenotazioni di prova
            print(f"Servizio riattivato: {nome}")


def crea_utenti(connessione) -> None:
    auth = AuthService(connessione)
    utenti = UtenteRepository(connessione)
    for email, nome, cognome, telefono in DIPENDENTI:
        if utenti.leggi_per_email(email) is None:
            auth.crea_staff(email, PASSWORD_DEMO, nome, cognome, telefono, "dipendente", True)
            print(f"Dipendente creato: {email}")
    for email, nome, cognome, telefono in CLIENTI + CLIENTI_STORICO:
        if utenti.leggi_per_email(email) is None:
            auth.registra(email, PASSWORD_DEMO, nome, cognome, telefono)
            print(f"Cliente creato: {email}")


def crea_prenotazioni(connessione) -> None:
    """
    Per ogni cliente di prova, se non ha ancora prenotazioni, ne crea e paga due in giorni diversi,
    usando lo stesso servizio del sito: slot liberi, transazione e conferma del pagamento.
    """
    provider = FakeProvider()
    prenotazioni = PrenotazioneService(connessione, provider)
    utenti = UtenteRepository(connessione)
    servizi = {s.nome: str(s.id) for s in SaloneService(connessione).elenca_servizi()}
    dipendenti = [utenti.leggi_per_email(email) for email, *_ in DIPENDENTI]
    scelte = [["Taglio"], ["Taglio e barba"]]
    adesso = datetime.now(UTC)

    for numero, (email, *_) in enumerate(CLIENTI):
        cliente = utenti.leggi_per_email(email)
        if prenotazioni.storico_cliente(cliente.id):
            continue
        for indice, nomi in enumerate(scelte):
            giorno = adesso.date() + timedelta(days=1 + numero + 2 * indice)
            ids = [servizi[nome] for nome in nomi if nome in servizi]
            dipendente = dipendenti[indice % len(dipendenti)]
            liberi = []
            while not liberi:
                liberi = prenotazioni.slot_per_scelta(str(dipendente.id), ids, giorno.isoformat(), adesso)
                if not liberi:
                    giorno += timedelta(days=1)  # giorno di chiusura: si passa al successivo
            inizio = liberi[len(liberi) // 3]
            _, url = prenotazioni.crea(cliente, str(dipendente.id), ids, giorno.isoformat(),
                                       inizio.strftime("%H:%M"), "acconto", adesso)
            prenotazioni.conferma_pagamento(url.rsplit("/", 1)[1], adesso)
            print(f"Prenotazione confermata: {email} con {dipendente.nome}, {giorno} {inizio:%H:%M}")


def crea_storico(connessione) -> None:
    """
    Prenotazioni passate e già pagate degli ultimi 4 mesi, per avere dati nelle statistiche.
    Le crea solo se nel periodo non ce ne sono. Il servizio del sito rifiuta gli orari passati,
    quindi qui si usano direttamente i repository, rispettando comunque turni e sovrapposizioni.
    """
    adesso = datetime.now(UTC)
    if StatisticheRepository(connessione).prenotazioni_confermate(
            in_utc(adesso - timedelta(days=GIORNI_STORICO)), in_utc(adesso)):
        return
    caso = random.Random(2026)  # a ogni esecuzione gli stessi dati
    disponibilita = DisponibilitaService(connessione)
    utenti = UtenteRepository(connessione)
    prenotazioni = PrenotazioneRepository(connessione)
    pagamenti = PagamentoRepository(connessione)
    percentuale = ImpostazioniRepository(connessione).leggi().percentuale_acconto
    servizi = SaloneService(connessione).elenca_servizi()
    pesi = [PESO_SERVIZI.get(s.nome, 1) for s in servizi]
    professionisti = [utenti.leggi_per_email(email) for email, *_ in DIPENDENTI]
    clienti = [utenti.leggi_per_email(email) for email, *_ in CLIENTI + CLIENTI_STORICO]
    occupati_cliente = {cliente.id: [] for cliente in clienti}
    create = 0

    for giorni_fa in range(GIORNI_STORICO, 0, -1):
        giorno = (adesso - timedelta(days=giorni_fa)).astimezone(disponibilita.fuso_orario).date()
        turni = disponibilita.turni_del_giorno(giorno)
        if not turni:
            continue
        crescita = (GIORNI_STORICO - giorni_fa) // 40  # più prenotazioni negli ultimi mesi
        for professionista in professionisti:
            occupati = []
            for _ in range(caso.randint(1, 4 + crescita)):
                servizio = caso.choices(servizi, weights=pesi)[0]
                durata = timedelta(minutes=servizio.durata_minuti)
                inizi = []
                for turno in turni:
                    inizio = datetime.combine(giorno, turno.ora_inizio, disponibilita.fuso_orario)
                    fine_turno = datetime.combine(giorno, turno.ora_fine, disponibilita.fuso_orario)
                    while inizio + durata <= fine_turno:
                        inizi.append(inizio)
                        inizio += timedelta(minutes=30)
                inizio = caso.choices(inizi, weights=[3 if i.hour in ORE_DI_PUNTA else 1 for i in inizi])[0]
                cliente = caso.choice(clienti)
                da, a = in_utc(inizio), in_utc(inizio + durata)
                if any(da < f and a > i for i, f in occupati + occupati_cliente[cliente.id]):
                    continue
                occupati.append((da, a))
                occupati_cliente[cliente.id].append((da, a))

                prenotata_il = da - timedelta(days=caso.randint(1, 10))
                modalita = caso.choice(["acconto", "completo"])
                prenotazione_id = prenotazioni.inserisci(Prenotazione(
                    cliente_id=cliente.id, dipendente_id=professionista.id, inizio=da, fine=a,
                    modalita_pagamento=modalita, scade_il=prenotata_il + timedelta(minutes=30),
                    stato="confermata",
                    servizi=[ServizioPrenotato(servizio.id, servizio.nome, servizio.durata_minuti,
                                               servizio.prezzo_centesimi)],
                ))
                pagato = servizio.prezzo_centesimi
                if modalita == "acconto":
                    pagato = calcola_acconto(servizio.prezzo_centesimi, percentuale)
                    pagamenti.inserisci(Pagamento(  # il resto, pagato in salone il giorno dell'appuntamento
                        tipo="in_sede", importo_centesimi=servizio.prezzo_centesimi - pagato,
                        prenotazione_id=prenotazione_id, stato="completato", creato_il=a,
                    ))
                pagamenti.inserisci(Pagamento(
                    tipo="online", importo_centesimi=pagato, prenotazione_id=prenotazione_id,
                    stato="completato", riferimento_provider="storico_" + secrets.token_hex(8),
                    creato_il=prenotata_il,
                ))
                create += 1
    connessione.commit()
    print(f"Storico creato: {create} prenotazioni passate negli ultimi {GIORNI_STORICO} giorni")


def main() -> None:
    load_dotenv()
    connessione = crea_connessione()
    try:
        crea_servizi(connessione)
        crea_utenti(connessione)
        crea_prenotazioni(connessione)
        crea_storico(connessione)
    finally:
        connessione.close()
    print(f"Fatto. Password dei profili di prova: {PASSWORD_DEMO}")


if __name__ == "__main__":
    main()

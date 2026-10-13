"""
Dati di prova per la demo: servizi, due dipendenti, due clienti e alcune prenotazioni confermate.
Si esegue dopo schema.sql e dopo flask crea-proprietario:  python seed.py
Si può rilanciare: salta ciò che esiste già. Le password dei profili di prova valgono solo in locale.
"""
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from app.db import crea_connessione
from app.pagamenti.finto import FakeProvider
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService
from app.servizi.prenotazione import PrenotazioneService
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
    for email, nome, cognome, telefono in CLIENTI:
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


def main() -> None:
    load_dotenv()
    connessione = crea_connessione()
    try:
        crea_servizi(connessione)
        crea_utenti(connessione)
        crea_prenotazioni(connessione)
    finally:
        connessione.close()
    print(f"Fatto. Password dei profili di prova: {PASSWORD_DEMO}")


if __name__ == "__main__":
    main()

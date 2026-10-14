"""
Dati di prova per la demo: cinque saloni immaginari (con proprietario, servizi e professionisti),
clienti, alcune prenotazioni future confermate e uno storico di 4 mesi di prenotazioni pagate per le statistiche.
Si esegue dopo schema.sql:  python seed.py
Si può rilanciare: salta ciò che esiste già. Le password dei profili di prova valgono solo in locale.
Nomi dei saloni, persone e numeri di telefono sono inventati; indirizzi e coordinate sono piazze pubbliche.
"""
import random
import secrets
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from app.db import crea_connessione
from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.modelli.recensione import Recensione
from app.pagamenti.finto import FakeProvider
from app.repository.salone import SaloneRepository
from app.repository.pagamento import PagamentoRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.recensione import RecensioneRepository
from app.repository.servizio import ServizioRepository
from app.repository.statistiche import StatisticheRepository
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService
from app.servizi.disponibilita import DisponibilitaService, in_utc
from app.servizi.prenotazione import PrenotazioneService, calcola_acconto
from app.servizi.salone import SaloneService
from app.servizi.saloni import SaloniService

PASSWORD_DEMO = "demo12345"

SERVIZI = [
    # nome, descrizione, durata in minuti, prezzo in euro
    ("Taglio", "Shampoo, taglio e asciugatura", "30", "18"),
    ("Barba", "Rifinitura con panno caldo", "30", "12"),
    ("Taglio e barba", "Il servizio completo", "60", "27"),
    ("Colore", "Colore e piega", "90", "45"),
    ("Piega", "Lavaggio e piega", "30", "15"),
]

# Saloni immaginari: dati del salone, proprietario (lavora anche in sala) e dipendenti.
SALONI = [
    {
        "salone": {"nome": "Barberia Plebiscito", "indirizzo": "Piazza del Plebiscito, 80132 Napoli",
                   "provincia": "NA", "telefono": "+390810000001", "coordinate": "40.835900, 14.248600",
                   "percentuale_acconto": "30"},
        "proprietario": ("titolare.napoli@demo.it", "Ciro", "Esposito", "+393330000001"),
        "dipendenti": [("marco@demo.it", "Marco", "Esposito", "+393331000001"),
                       ("giulia@demo.it", "Giulia", "Russo", "+393331000002")],
    },
    {
        "salone": {"nome": "Salone Rione Terra", "indirizzo": "Piazza della Repubblica, 80078 Pozzuoli",
                   "provincia": "NA", "telefono": "+390810000002", "coordinate": "40.823300, 14.121000",
                   "percentuale_acconto": "20"},
        "proprietario": ("titolare.pozzuoli@demo.it", "Rosa", "Coppola", "+393330000002"),
        "dipendenti": [("tommaso@demo.it", "Tommaso", "Iovine", "+393331000003")],
    },
    {
        "salone": {"nome": "Barbiere del Lungomare", "indirizzo": "Piazza della Libertà, 84121 Salerno",
                   "provincia": "SA", "telefono": "+390890000001", "coordinate": "40.674700, 14.753400",
                   "percentuale_acconto": "30"},
        "proprietario": ("titolare.salerno@demo.it", "Antonio", "Senatore", "+393330000003"),
        "dipendenti": [("federica@demo.it", "Federica", "Amato", "+393331000004")],
    },
    {
        "salone": {"nome": "Salone della Reggia", "indirizzo": "Piazza Carlo di Borbone, 81100 Caserta",
                   "provincia": "CE", "telefono": "+390823000001", "coordinate": "41.072700, 14.327700",
                   "percentuale_acconto": "40"},
        "proprietario": ("titolare.caserta@demo.it", "Lucia", "Natale", "+393330000004"),
        "dipendenti": [],
    },
    {
        "salone": {"nome": "Barberia Capitolina", "indirizzo": "Piazza Venezia, 00186 Roma",
                   "provincia": "RM", "telefono": "+390600000001", "coordinate": "41.895900, 12.482600",
                   "percentuale_acconto": "30"},
        "proprietario": ("titolare.roma@demo.it", "Fabio", "Ricci", "+393330000005"),
        "dipendenti": [("stefano@demo.it", "Stefano", "Bruno", "+393331000005")],
    },
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

# Recensioni dello storico: una prenotazione su tre ne riceve una, con voti diversi da salone a salone.
COMMENTI = {
    5: ["Bravissimi, ci torno di sicuro.", "Taglio perfetto e puntuali.", "Ambiente curato e personale gentile.", None],
    4: ["Molto bene, solo un po' di attesa.", "Ottimo servizio.", None],
    3: ["Nella media.", "Taglio ok, prezzo un po' alto.", None],
    2: ["Ritardo di venti minuti.", None],
    1: ["Non mi sono trovato bene.", None],
}
PESI_VOTI = [  # pesi dei voti 1-5 per ogni salone di SALONI, nello stesso ordine
    [0, 1, 2, 6, 12], [1, 1, 3, 8, 6], [0, 0, 1, 5, 14], [1, 2, 6, 6, 3], [0, 1, 3, 9, 8],
]


def crea_saloni(connessione) -> list[int]:
    """
    Crea i saloni con il loro proprietario, i servizi e i dipendenti, se non esistono già.
    Returns: gli id dei saloni, nell'ordine di SALONI.
    """
    saloni = SaloniService(connessione)
    auth = AuthService(connessione)
    utenti = UtenteRepository(connessione)
    ids = []
    for dati in SALONI:
        esistente = SaloneRepository(connessione).leggi_per_nome(dati["salone"]["nome"])
        if esistente is None:
            email, nome, cognome, telefono = dati["proprietario"]
            salone_id, _ = saloni.crea_con_proprietario(dati["salone"], {
                "email": email, "password": PASSWORD_DEMO, "nome": nome, "cognome": cognome,
                "telefono": telefono, "riceve_prenotazioni": True,
            })
            print(f"Salone creato: {dati['salone']['nome']} (proprietario {email})")
        else:
            salone_id = esistente.id
        ids.append(salone_id)
        crea_servizi(connessione, salone_id)
        for email, nome, cognome, telefono in dati["dipendenti"]:
            if utenti.leggi_per_email(email) is None:
                auth.crea_staff(email, PASSWORD_DEMO, nome, cognome, telefono, "dipendente", True, salone_id)
                print(f"Dipendente creato: {email}")
    return ids


def crea_servizi(connessione, salone_id: int) -> None:
    salone = SaloneService(connessione, salone_id)
    for nome, descrizione, durata, prezzo in SERVIZI:
        esistente = ServizioRepository(connessione).leggi_per_nome(salone_id, nome)
        if esistente is None:
            salone.crea_servizio(nome, descrizione, durata, prezzo)
        elif not esistente.attivo:
            salone.imposta_attivo(esistente.id, True)  # servono attivi per le prenotazioni di prova


def crea_clienti(connessione) -> None:
    auth = AuthService(connessione)
    utenti = UtenteRepository(connessione)
    for email, nome, cognome, telefono in CLIENTI + CLIENTI_STORICO:
        if utenti.leggi_per_email(email) is None:
            auth.registra(email, PASSWORD_DEMO, nome, cognome, telefono)
            print(f"Cliente creato: {email}")


def crea_prenotazioni(connessione, saloni_ids: list[int]) -> None:
    """
    Per ogni cliente di prova, se non ha ancora prenotazioni, ne crea e paga due in giorni diversi
    e in due saloni diversi, usando lo stesso servizio del sito: slot liberi, transazione e conferma del pagamento.
    """
    provider = FakeProvider()
    prenotazioni = PrenotazioneService(connessione, provider)
    utenti = UtenteRepository(connessione)
    scelte = [(saloni_ids[0], ["Taglio"]), (saloni_ids[2], ["Taglio e barba"])]
    adesso = datetime.now(UTC)

    for numero, (email, *_) in enumerate(CLIENTI):
        cliente = utenti.leggi_per_email(email)
        if prenotazioni.storico_cliente(cliente.id):
            continue
        for indice, (salone_id, nomi) in enumerate(scelte):
            servizi = {s.nome: str(s.id) for s in SaloneService(connessione, salone_id).elenca_servizi()}
            professionisti = utenti.elenca_professionisti(salone_id)
            giorno = adesso.date() + timedelta(days=1 + numero + 2 * indice)
            ids = [servizi[nome] for nome in nomi if nome in servizi]
            dipendente = professionisti[numero % len(professionisti)]
            liberi = []
            while not liberi:
                liberi = prenotazioni.slot_per_scelta(salone_id, str(dipendente.id), ids, giorno.isoformat(), adesso)
                if not liberi:
                    giorno += timedelta(days=1)  # giorno di chiusura: si passa al successivo
            inizio = liberi[len(liberi) // 3]
            _, url = prenotazioni.crea(cliente, salone_id, str(dipendente.id), ids, giorno.isoformat(),
                                       inizio.strftime("%H:%M"), "acconto", adesso)
            prenotazioni.conferma_pagamento(url.rsplit("/", 1)[1], adesso)
            print(f"Prenotazione confermata: {email} con {dipendente.nome}, {giorno} {inizio:%H:%M}")


def crea_storico(connessione, salone_id: int, caso: random.Random, pesi_voti: list[int]) -> None:
    """
    Prenotazioni passate e già pagate degli ultimi 4 mesi in un salone, per avere dati nelle statistiche.
    Le crea solo se nel periodo il salone non ne ha. Il servizio del sito rifiuta gli orari passati,
    quindi qui si usano direttamente i repository, rispettando comunque turni e sovrapposizioni.
    """
    adesso = datetime.now(UTC)
    if StatisticheRepository(connessione).prenotazioni_confermate(
            salone_id, in_utc(adesso - timedelta(days=GIORNI_STORICO)), in_utc(adesso)):
        return
    disponibilita = DisponibilitaService(connessione, salone_id)
    utenti = UtenteRepository(connessione)
    prenotazioni = PrenotazioneRepository(connessione)
    pagamenti = PagamentoRepository(connessione)
    recensioni = RecensioneRepository(connessione)
    percentuale = disponibilita.salone.percentuale_acconto
    servizi = SaloneService(connessione, salone_id).elenca_servizi()
    pesi = [PESO_SERVIZI.get(s.nome, 1) for s in servizi]
    professionisti = utenti.elenca_professionisti(salone_id)
    # Solo i clienti dello storico: l'area personale di anna e luca resta leggibile, con le sole prenotazioni future.
    clienti = [utenti.leggi_per_email(email) for email, *_ in CLIENTI_STORICO]
    # Prenotazioni già presenti dei clienti (anche in altri saloni): un cliente non è in due posti insieme.
    occupati_cliente = {cliente.id: prenotazioni.intervalli_occupati_cliente(
        cliente.id, in_utc(adesso - timedelta(days=GIORNI_STORICO + 1)), in_utc(adesso), in_utc(adesso))
        for cliente in clienti}
    create = 0

    for giorni_fa in range(GIORNI_STORICO, 0, -1):
        giorno = (adesso - timedelta(days=giorni_fa)).astimezone(disponibilita.fuso_orario).date()
        turni = disponibilita.turni_del_giorno(giorno)
        if not turni:
            continue
        crescita = (GIORNI_STORICO - giorni_fa) // 40  # più prenotazioni negli ultimi mesi
        for professionista in professionisti:
            occupati = []
            for _ in range(caso.randint(1, 3 + crescita)):
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
                    salone_id=salone_id, cliente_id=cliente.id, dipendente_id=professionista.id, inizio=da, fine=a,
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
                if caso.random() < 0.33:
                    voto = caso.choices(range(1, 6), weights=pesi_voti)[0]
                    recensioni.inserisci(Recensione(
                        prenotazione_id=prenotazione_id, salone_id=salone_id, cliente_id=cliente.id, voto=voto,
                        commento=caso.choice(COMMENTI[voto]),
                        creato_il=min(a + timedelta(days=caso.randint(0, 3)), in_utc(adesso)),  # mai nel futuro
                    ))
                create += 1
    connessione.commit()
    print(f"Storico creato per {disponibilita.salone.nome}: {create} prenotazioni negli ultimi {GIORNI_STORICO} giorni")


def main() -> None:
    load_dotenv()
    connessione = crea_connessione()
    try:
        saloni_ids = crea_saloni(connessione)
        crea_clienti(connessione)
        crea_prenotazioni(connessione, saloni_ids)
        caso = random.Random(2026)  # a ogni esecuzione gli stessi dati
        for salone_id, pesi_voti in zip(saloni_ids, PESI_VOTI):
            crea_storico(connessione, salone_id, caso, pesi_voti)
    finally:
        connessione.close()
    print(f"Fatto. Password dei profili di prova: {PASSWORD_DEMO}")


if __name__ == "__main__":
    main()

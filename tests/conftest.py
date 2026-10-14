import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from app import create_app
from app.db import crea_connessione
from app.modelli.salone import Salone
from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.repository.orario import OrarioRepository
from app.repository.salone import SaloneRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository
from app.servizi.saloni import ORARIO_DI_PARTENZA

load_dotenv()
# Tutti i test usano il database di prova, anche le richieste inviate all'app.
os.environ["DB_NAME"] = "barber_booking_test"

DOMINIO_UTENTI_ACCESSI = "@accessi.test"
NOME_SALONE_TEST = "Salone di prova dei test"
NOME_ALTRO_SALONE_TEST = "Altro salone dei test"


def _salone_di_prova(nome: str, provincia: str, coordinate: tuple[str, str]) -> int:
    """
    Salone dei test, salvato con commit reale la prima volta e poi riusato (come i dati iniziali dello schema):
    calendario di partenza, acconto del 30% e 3 mesi prenotabili.
    Returns: l'id del salone.
    """
    connessione = crea_connessione()
    esistente = SaloneRepository(connessione).leggi_per_nome(nome)
    if esistente is not None:
        connessione.close()
        return esistente.id
    salone_id = SaloneRepository(connessione).inserisci(Salone(
        nome, "Via di prova 1", provincia, "+390000000000", Decimal(coordinate[0]), Decimal(coordinate[1]),
    ))
    orari = OrarioRepository(connessione)
    for giorno, turni in ORARIO_DI_PARTENZA.items():
        for turno in turni:
            orari.inserisci_turno_settimanale(salone_id, giorno, turno)
    connessione.commit()
    connessione.close()
    return salone_id


@pytest.fixture(scope="session")
def salone_test() -> int:
    """
    Id del salone usato da quasi tutti i test (provincia di Napoli).
    """
    return _salone_di_prova(NOME_SALONE_TEST, "NA", ("40.851800", "14.268100"))


@pytest.fixture(scope="session")
def altro_salone_test() -> int:
    """
    Id di un secondo salone, per i test di isolamento tra saloni (provincia di Roma).
    """
    return _salone_di_prova(NOME_ALTRO_SALONE_TEST, "RM", ("41.902800", "12.496400"))


@pytest.fixture
def conn(monkeypatch):
    """
    Connessione al database di prova con commit disattivato: il rollback finale annulla tutte le modifiche.
    """
    connessione = crea_connessione()
    monkeypatch.setattr(connessione, "commit", lambda: None)
    yield connessione
    connessione.rollback()
    connessione.close()


@pytest.fixture
def app():
    """
    App Flask di prova, con la protezione CSRF spenta per inviare moduli senza token.
    """
    return create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})


@pytest.fixture
def client(app):
    """
    Client che simula il browser: invia richieste all'app senza avviare il server.
    """
    return app.test_client()


def _cancella_utenti_accessi(connessione) -> None:
    """
    Cancella gli utenti creati da utenti_accessi, compresi i resti di un'esecuzione interrotta.
    """
    with connessione.cursor() as cur:
        cur.execute("DELETE FROM utenti WHERE email LIKE %s", ("%" + DOMINIO_UTENTI_ACCESSI,))
    connessione.commit()


@pytest.fixture(scope="session")
def utenti_accessi(salone_test):
    """
    Crea con un commit reale un utente per ruolo, visibile alle richieste dell'app, e lo cancella a fine test.
    Returns: dizionario ruolo -> id dell'utente.
    """
    connessione = crea_connessione()
    _cancella_utenti_accessi(connessione)
    repo = UtenteRepository(connessione)
    ids = {}
    for ruolo in ("cliente", "dipendente", "proprietario"):
        ids[ruolo] = repo.inserisci(Utente(
            email=ruolo + DOMINIO_UTENTI_ACCESSI,
            password_hash="hash-finto",
            nome="Prova",
            cognome="Accessi",
            telefono="3330000000",
            ruolo=ruolo,
            salone_id=None if ruolo == "cliente" else salone_test,
            riceve_prenotazioni=(ruolo != "cliente"),
        ))
    connessione.commit()
    yield ids
    _cancella_utenti_accessi(connessione)
    connessione.close()


@pytest.fixture
def salone(conn, salone_test):
    """
    Dati di prova per le prenotazioni nel salone dei test (annullati dal rollback): un cliente,
    due professionisti e due servizi da 30 minuti, Taglio a 20 € e Barba a 15,50 €.
    Returns: dizionario con gli id (salone compreso) e l'Utente cliente.
    """
    utenti = UtenteRepository(conn)
    servizi = ServizioRepository(conn)
    cliente_id = utenti.inserisci(Utente("cliente@salone.test", "hash-finto", "Carla", "Cliente", "3330000001"))
    return {
        "salone_id": salone_test,
        "cliente": utenti.leggi_per_id(cliente_id),
        "dipendente_id": utenti.inserisci(Utente(
            "dipendente@salone.test", "hash-finto", "Dario", "Dipendente", "3330000002",
            ruolo="dipendente", salone_id=salone_test, riceve_prenotazioni=True,
        )),
        "altro_dipendente_id": utenti.inserisci(Utente(
            "altro@salone.test", "hash-finto", "Alba", "Altra", "3330000003",
            ruolo="dipendente", salone_id=salone_test, riceve_prenotazioni=True,
        )),
        "taglio_id": servizi.inserisci(Servizio("Taglio prova", 30, 2000, salone_id=salone_test)),
        "barba_id": servizi.inserisci(Servizio("Barba prova", 30, 1550, salone_id=salone_test)),
    }

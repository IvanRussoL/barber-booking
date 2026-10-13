import threading
import time as orologio
from datetime import UTC, datetime

import pytest

from app.db import crea_connessione
from app.eccezioni import SlotNonDisponibileError
from app.modelli.prenotazione import Prenotazione
from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.pagamenti.finto import FakeProvider
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository
from app.servizi.prenotazione import PrenotazioneService

ADESSO = datetime(2026, 10, 13, 6, 0, tzinfo=UTC)
DOMINIO = "@concorrenza.test"


def _pulisci(conn) -> None:
    """
    Cancella i dati del test nell'ordine imposto dalle chiavi esterne, con un commit reale.
    """
    with conn.cursor() as cur:
        filtro = "SELECT id FROM utenti WHERE email LIKE %s"
        cur.execute(f"DELETE FROM pagamenti WHERE prenotazione_id IN "
                    f"(SELECT id FROM prenotazioni WHERE cliente_id IN ({filtro}))", ("%" + DOMINIO,))
        cur.execute(f"DELETE FROM prenotazioni_servizi WHERE prenotazione_id IN "
                    f"(SELECT id FROM prenotazioni WHERE cliente_id IN ({filtro}))", ("%" + DOMINIO,))
        cur.execute(f"DELETE FROM prenotazioni WHERE cliente_id IN ({filtro})", ("%" + DOMINIO,))
        cur.execute("DELETE FROM servizi WHERE nome = 'Servizio concorrenza'")
        cur.execute("DELETE FROM utenti WHERE email LIKE %s", ("%" + DOMINIO,))
    conn.commit()


@pytest.fixture
def dati_confermati():
    """
    Due clienti, un dipendente e un servizio salvati con commit reale: due connessioni diverse
    vedono solo dati confermati. Cancellati a fine test.
    """
    conn = crea_connessione()
    _pulisci(conn)
    utenti = UtenteRepository(conn)
    dati = {
        "cliente_a": utenti.inserisci(Utente("a" + DOMINIO, "x", "Anna", "Prima", "3330000010")),
        "cliente_b": utenti.inserisci(Utente("b" + DOMINIO, "x", "Bruno", "Secondo", "3330000011")),
        "dipendente": utenti.inserisci(Utente("d" + DOMINIO, "x", "Dino", "Dipendente", "3330000012",
                                              ruolo="dipendente", riceve_prenotazioni=True)),
        "servizio": ServizioRepository(conn).inserisci(Servizio("Servizio concorrenza", 30, 1000)),
    }
    conn.commit()
    dati["cliente_b"] = utenti.leggi_per_id(dati["cliente_b"])
    yield dati
    _pulisci(conn)
    conn.close()


def test_due_richieste_simultanee_sullo_stesso_slot(dati_confermati):
    conn_a = crea_connessione()
    conn_b = crea_connessione()
    risultato = {}

    # Richiesta A: blocca il dipendente e salva le 10:00 (08:00 UTC), ma non ha ancora fatto commit.
    UtenteRepository(conn_a).blocca(dati_confermati["dipendente"])
    PrenotazioneRepository(conn_a).inserisci(Prenotazione(
        cliente_id=dati_confermati["cliente_a"], dipendente_id=dati_confermati["dipendente"],
        inizio=datetime(2026, 10, 14, 8, 0), fine=datetime(2026, 10, 14, 8, 30),
        modalita_pagamento="completo", scade_il=datetime(2026, 10, 13, 6, 30),
    ))

    # Richiesta B, in parallelo: vuole lo stesso orario.
    def richiesta_b():
        try:
            PrenotazioneService(conn_b, FakeProvider()).crea(
                dati_confermati["cliente_b"], str(dati_confermati["dipendente"]),
                [str(dati_confermati["servizio"])], "2026-10-14", "10:00", "completo", ADESSO,
            )
            risultato["esito"] = "prenotata"
        except SlotNonDisponibileError:
            risultato["esito"] = "rifiutata"

    thread_b = threading.Thread(target=richiesta_b)
    thread_b.start()
    orologio.sleep(1)
    assert thread_b.is_alive(), "B deve aspettare che A liberi il blocco sul dipendente"

    conn_a.commit()  # A finisce: B riparte e ricontrolla lo slot
    thread_b.join(timeout=10)
    conn_b.rollback()
    conn_a.close()
    conn_b.close()
    assert risultato["esito"] == "rifiutata"

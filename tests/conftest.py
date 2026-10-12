import pytest
from dotenv import load_dotenv

from app.db import crea_connessione

load_dotenv()


@pytest.fixture
def conn(monkeypatch):
    """
    Connessione al database di prova; a fine test annulla tutte le modifiche con rollback.
    """
    monkeypatch.setenv("DB_NAME", "barber_booking_test")
    connessione = crea_connessione()
    yield connessione
    connessione.rollback()
    connessione.close()
import mysql.connector
import pytest

from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.repository.impostazioni import ImpostazioniRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository


# --- Impostazioni ---

def test_impostazioni_lette_dalla_riga_iniziale(conn):
    impostazioni = ImpostazioniRepository(conn).leggi()
    assert impostazioni.id == 1
    assert impostazioni.percentuale_acconto == 30
    assert impostazioni.fuso_orario == "Europe/Rome"


# --- Servizi ---

def test_servizio_inserito_e_riletto(conn):
    repo = ServizioRepository(conn)
    nuovo_id = repo.inserisci(Servizio("Taglio test", 30, 1500))
    assert repo.leggi_per_id(nuovo_id) == Servizio("Taglio test", 30, 1500, id=nuovo_id)


def test_servizio_inesistente_restituisce_none(conn):
    assert ServizioRepository(conn).leggi_per_id(0) is None


def test_elenco_esclude_i_servizi_disattivati(conn):
    repo = ServizioRepository(conn)
    repo.inserisci(Servizio("Attivo test", 30, 1000))
    repo.inserisci(Servizio("Disattivo test", 30, 1000, attivo=False))
    nomi_attivi = [s.nome for s in repo.elenca()]
    nomi_tutti = [s.nome for s in repo.elenca(solo_attivi=False)]
    assert "Attivo test" in nomi_attivi
    assert "Disattivo test" not in nomi_attivi
    assert "Disattivo test" in nomi_tutti


def test_servizio_aggiornato(conn):
    repo = ServizioRepository(conn)
    servizio = repo.leggi_per_id(repo.inserisci(Servizio("Barba test", 30, 800)))
    servizio.prezzo_centesimi = 1000
    repo.aggiorna(servizio)
    assert repo.leggi_per_id(servizio.id).prezzo_centesimi == 1000


def test_nome_servizio_duplicato_rifiutato(conn):
    repo = ServizioRepository(conn)
    repo.inserisci(Servizio("Doppio test", 30, 1000))
    with pytest.raises(mysql.connector.IntegrityError):
        repo.inserisci(Servizio("Doppio test", 60, 2000))


# --- Utenti ---

def _utente_di_prova(email: str) -> Utente:
    return Utente(email, "hash-finto", "Mario", "Rossi", "3330000000")


def test_utente_letto_per_id_ed_email_senza_maiuscole(conn):
    repo = UtenteRepository(conn)
    nuovo_id = repo.inserisci(_utente_di_prova("mario@test.it"))
    per_id = repo.leggi_per_id(nuovo_id)
    per_email = repo.leggi_per_email("MARIO@test.it")
    assert per_id == per_email
    assert per_id.ruolo == "cliente"
    assert per_id.attivo is True
    assert per_id.creato_il is not None


def test_email_duplicata_rifiutata(conn):
    repo = UtenteRepository(conn)
    repo.inserisci(_utente_di_prova("doppio@test.it"))
    with pytest.raises(mysql.connector.IntegrityError):
        repo.inserisci(_utente_di_prova("DOPPIO@test.it"))
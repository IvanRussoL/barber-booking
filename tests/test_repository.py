import mysql.connector
import pytest

from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.repository.salone import SaloneRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository


# --- Saloni ---

def test_salone_letto_con_i_valori_predefiniti(conn, salone_test):
    salone = SaloneRepository(conn).leggi_per_id(salone_test)
    assert salone.id == salone_test
    assert salone.provincia == "NA"
    assert salone.percentuale_acconto == 30
    assert salone.fuso_orario == "Europe/Rome"
    assert salone.attivo is True


def test_salone_inesistente_restituisce_none(conn):
    assert SaloneRepository(conn).leggi_per_id(0) is None


# --- Servizi ---

def test_servizio_inserito_e_riletto(conn, salone_test):
    repo = ServizioRepository(conn)
    nuovo_id = repo.inserisci(Servizio("Taglio test", 30, 1500, salone_id=salone_test))
    assert repo.leggi_per_id(salone_test, nuovo_id) == Servizio("Taglio test", 30, 1500, salone_id=salone_test,
                                                                id=nuovo_id)


def test_servizio_inesistente_o_di_un_altro_salone(conn, salone_test, altro_salone_test):
    repo = ServizioRepository(conn)
    assert repo.leggi_per_id(salone_test, 0) is None
    nuovo_id = repo.inserisci(Servizio("Taglio test", 30, 1500, salone_id=salone_test))
    assert repo.leggi_per_id(altro_salone_test, nuovo_id) is None


def test_elenco_esclude_i_servizi_disattivati(conn, salone_test):
    repo = ServizioRepository(conn)
    repo.inserisci(Servizio("Attivo test", 30, 1000, salone_id=salone_test))
    repo.inserisci(Servizio("Disattivo test", 30, 1000, salone_id=salone_test, attivo=False))
    nomi_attivi = [s.nome for s in repo.elenca(salone_test)]
    nomi_tutti = [s.nome for s in repo.elenca(salone_test, solo_attivi=False)]
    assert "Attivo test" in nomi_attivi
    assert "Disattivo test" not in nomi_attivi
    assert "Disattivo test" in nomi_tutti


def test_servizio_aggiornato(conn, salone_test):
    repo = ServizioRepository(conn)
    servizio = repo.leggi_per_id(salone_test, repo.inserisci(Servizio("Barba test", 30, 800, salone_id=salone_test)))
    servizio.prezzo_centesimi = 1000
    repo.aggiorna(servizio)
    assert repo.leggi_per_id(salone_test, servizio.id).prezzo_centesimi == 1000


def test_nome_servizio_duplicato_rifiutato_nello_stesso_salone(conn, salone_test, altro_salone_test):
    repo = ServizioRepository(conn)
    repo.inserisci(Servizio("Doppio test", 30, 1000, salone_id=salone_test))
    repo.inserisci(Servizio("Doppio test", 30, 1000, salone_id=altro_salone_test))  # altro salone: permesso
    with pytest.raises(mysql.connector.IntegrityError):
        repo.inserisci(Servizio("Doppio test", 60, 2000, salone_id=salone_test))


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

def test_staff_senza_salone_e_cliente_con_salone_rifiutati(conn, salone_test):
    # Il vincolo CHECK chk_utenti_salone: MySQL lo segnala come DatabaseError (codice 3819).
    repo = UtenteRepository(conn)
    with pytest.raises(mysql.connector.DatabaseError):
        repo.inserisci(Utente("staff@test.it", "x", "Mario", "Rossi", "3330000000", ruolo="dipendente"))
    with pytest.raises(mysql.connector.DatabaseError):
        repo.inserisci(Utente("cliente@test.it", "x", "Mario", "Rossi", "3330000000", salone_id=salone_test))

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app.eccezioni import CredenzialiNonValideError, DatiNonValidiError, EmailGiaRegistrataError
from app.modelli.utente import Utente
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService

DATI_VALIDI = {
    "email": " Mario.Rossi@Test.it ",
    "password": "password123",
    "nome": "Mario",
    "cognome": "Rossi",
    "telefono": "+39 333 1234567",
}


def _registra(conn, **modifiche) -> int:
    """
    Registra un cliente con i DATI_VALIDI, sostituendo i campi passati come argomenti.
    """
    return AuthService(conn).registra(**(DATI_VALIDI | modifiche))


# --- Registrazione ---

def test_registrazione_crea_un_cliente_con_dati_ripuliti(conn):
    utente = UtenteRepository(conn).leggi_per_id(_registra(conn))
    assert utente.email == "mario.rossi@test.it"
    assert utente.telefono == "+393331234567"
    assert utente.ruolo == "cliente"
    assert utente.riceve_prenotazioni is False
    assert utente.password_hash != "password123"
    assert check_password_hash(utente.password_hash, "password123")


def test_email_gia_registrata_anche_con_maiuscole_diverse(conn):
    _registra(conn)
    with pytest.raises(EmailGiaRegistrataError):
        _registra(conn, email="MARIO.ROSSI@test.it")


@pytest.mark.parametrize("campo, valore", [
    ("email", "   "),
    ("email", "senza-chiocciola"),
    ("password", "corta"),
    ("nome", "Mario2"),
    ("nome", "a" * 101),
    ("cognome", "-'"),
    ("telefono", "333abc4567"),
    ("telefono", "12345"),
])
def test_dati_non_validi_rifiutati(conn, campo, valore):
    with pytest.raises(DatiNonValidiError):
        _registra(conn, **{campo: valore})


@pytest.mark.parametrize("nome, cognome", [
    ("Nicolò", "D'Angelo"),
    ("Anna-Maria", "De Luca"),
    ("José", "D’Amico"),
])
def test_nomi_reali_accettati(conn, nome, cognome):
    utente = UtenteRepository(conn).leggi_per_id(_registra(conn, nome=nome, cognome=cognome))
    assert (utente.nome, utente.cognome) == (nome, cognome)


# --- Creazione di dipendenti e proprietario ---

def test_crea_staff_proprietario_che_riceve_prenotazioni(conn):
    servizio = AuthService(conn)
    utente_id = servizio.crea_staff(**DATI_VALIDI, ruolo="proprietario", riceve_prenotazioni=True)
    utente = UtenteRepository(conn).leggi_per_id(utente_id)
    assert utente.ruolo == "proprietario"
    assert utente.riceve_prenotazioni is True


def test_crea_staff_rifiuta_il_ruolo_cliente(conn):
    with pytest.raises(DatiNonValidiError):
        AuthService(conn).crea_staff(**DATI_VALIDI, ruolo="cliente", riceve_prenotazioni=False)


# --- Login ---

def test_login_corretto_senza_badare_a_maiuscole_e_spazi(conn):
    utente_id = _registra(conn)
    utente = AuthService(conn).autentica(" MARIO.rossi@test.it", "password123")
    assert utente.id == utente_id


@pytest.mark.parametrize("email, password", [
    ("mario.rossi@test.it", "password-sbagliata"),
    ("nessuno@test.it", "password123"),
])
def test_credenziali_errate_con_lo_stesso_messaggio(conn, email, password):
    _registra(conn)
    with pytest.raises(CredenzialiNonValideError, match="Email o password non corretti"):
        AuthService(conn).autentica(email, password)


def test_account_disattivato_non_accede(conn):
    UtenteRepository(conn).inserisci(Utente(
        "spento@test.it", generate_password_hash("password123"),
        "Mario", "Rossi", "3330000000", attivo=False,
    ))
    with pytest.raises(CredenzialiNonValideError, match="disattivato"):
        AuthService(conn).autentica("spento@test.it", "password123")

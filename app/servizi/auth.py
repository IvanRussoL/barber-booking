import re

from werkzeug.security import check_password_hash, generate_password_hash

from app.eccezioni import CredenzialiNonValideError, DatiNonValidiError, EmailGiaRegistrataError
from app.modelli.utente import Utente
from app.repository.utente import UtenteRepository
from app.servizi.validazione import testo_obbligatorio

LUNGHEZZA_MINIMA_PASSWORD = 8
CARATTERI_AMMESSI_NOME = " '’-"
RUOLI_STAFF = ("dipendente", "proprietario")


def _nome_valido(valore: str, campo: str) -> str:
    """
    Controlla un nome o un cognome: lettere di qualsiasi alfabeto, spazi, apostrofi e trattini.
    Returns: il testo ripulito.
    Raises: DatiNonValidiError se è vuoto, troppo lungo, senza lettere o con cifre e simboli.
    """
    valore = testo_obbligatorio(valore, campo, 100)
    solo_caratteri_ammessi = all(c.isalpha() or c in CARATTERI_AMMESSI_NOME for c in valore)
    if not solo_caratteri_ammessi or not any(c.isalpha() for c in valore):
        raise DatiNonValidiError(
            f"Il campo {campo} può contenere solo lettere, spazi, apostrofi e trattini."
        )
    return valore


class AuthService:
    """
    Registrazione e login degli utenti.
    """

    def __init__(self, connessione):
        self._conn = connessione
        self._utenti = UtenteRepository(connessione)

    def registra(self, email: str, password: str, nome: str, cognome: str, telefono: str) -> int:
        """
        Registra un nuovo cliente: è l'unico ruolo che si può ottenere dalla pagina pubblica.
        Returns: l'id del nuovo utente.
        Raises: DatiNonValidiError se un dato non è valido; EmailGiaRegistrataError se l'email è già usata.
        """
        return self._crea_utente(email, password, nome, cognome, telefono, "cliente", False)

    def crea_staff(self, email: str, password: str, nome: str, cognome: str, telefono: str,
                   ruolo: str, riceve_prenotazioni: bool) -> int:
        """
        Crea un dipendente o un proprietario; usato dal comando crea-proprietario e da seed.py.
        Returns: l'id del nuovo utente.
        Raises: DatiNonValidiError se il ruolo non è dipendente o proprietario o un dato non è valido;
            EmailGiaRegistrataError se l'email è già usata.
        """
        if ruolo not in RUOLI_STAFF:
            raise DatiNonValidiError("Il ruolo deve essere dipendente o proprietario.")
        return self._crea_utente(email, password, nome, cognome, telefono, ruolo, riceve_prenotazioni)

    def _crea_utente(self, email: str, password: str, nome: str, cognome: str, telefono: str,
                     ruolo: str, riceve_prenotazioni: bool) -> int:
        """
        Controlla i dati, salva l'utente con la password trasformata in hash e conferma con commit.
        Returns: l'id del nuovo utente.
        Raises: DatiNonValidiError se un dato non è valido; EmailGiaRegistrataError se l'email è già usata.
        """
        email = testo_obbligatorio(email, "email", 255).lower()
        if "@" not in email:
            raise DatiNonValidiError("L'email non è valida.")
        if len(password) < LUNGHEZZA_MINIMA_PASSWORD:
            raise DatiNonValidiError(
                f"La password deve avere almeno {LUNGHEZZA_MINIMA_PASSWORD} caratteri."
            )
        nome = _nome_valido(nome, "nome")
        cognome = _nome_valido(cognome, "cognome")
        telefono = testo_obbligatorio(telefono, "telefono", 20).replace(" ", "")
        if not re.fullmatch(r"\+?[0-9]{6,15}", telefono):
            raise DatiNonValidiError(
                "Il telefono deve contenere solo cifre, con il + iniziale facoltativo."
            )

        if self._utenti.leggi_per_email(email) is not None:
            raise EmailGiaRegistrataError("Esiste già un account con questa email.")

        utente = Utente(
            email=email,
            password_hash=generate_password_hash(password),
            nome=nome,
            cognome=cognome,
            telefono=telefono,
            ruolo=ruolo,
            riceve_prenotazioni=riceve_prenotazioni,
        )
        utente_id = self._utenti.inserisci(utente)
        self._conn.commit()
        return utente_id

    def autentica(self, email: str, password: str) -> Utente:
        """
        Controlla email e password per il login.
        Returns: l'Utente, se le credenziali sono corrette e l'account è attivo.
        Raises: CredenzialiNonValideError se email o password sono errate o l'account è disattivato.
        """
        utente = self._utenti.leggi_per_email(email.strip().lower())
        if utente is None or not check_password_hash(utente.password_hash, password):
            raise CredenzialiNonValideError("Email o password non corretti.")
        if not utente.attivo:
            raise CredenzialiNonValideError("Account disattivato: contatta il salone.")
        return utente
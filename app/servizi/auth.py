from werkzeug.security import check_password_hash, generate_password_hash

from app.eccezioni import CredenzialiNonValideError, DatiNonValidiError, EmailGiaRegistrataError
from app.modelli.utente import Utente
from app.repository.utente import UtenteRepository
from app.repository.salone import SaloneRepository
from app.servizi.validazione import telefono_valido, testo_obbligatorio

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
        return self._salva(self.utente_valido(email, password, nome, cognome, telefono))

    def crea_staff(self, email: str, password: str, nome: str, cognome: str, telefono: str,
                   ruolo: str, riceve_prenotazioni: bool, salone_id: int) -> int:
        """
        Crea un dipendente o un proprietario di un salone esistente; usato dal comando crea-proprietario
        e da seed.py.
        Returns: l'id del nuovo utente.
        Raises: DatiNonValidiError se il ruolo non è dipendente o proprietario, il salone non esiste
            o un dato non è valido; EmailGiaRegistrataError se l'email è già usata.
        """
        if ruolo not in RUOLI_STAFF:
            raise DatiNonValidiError("Il ruolo deve essere dipendente o proprietario.")
        if SaloneRepository(self._conn).leggi_per_id(salone_id) is None:
            raise DatiNonValidiError("Il salone indicato non esiste.")
        utente = self.utente_valido(email, password, nome, cognome, telefono, ruolo, riceve_prenotazioni)
        utente.salone_id = salone_id
        return self._salva(utente)

    def _salva(self, utente: Utente) -> int:
        """
        Inserisce l'utente già controllato e conferma con commit.
        Returns: l'id del nuovo utente.
        """
        utente_id = self._utenti.inserisci(utente)
        self._conn.commit()
        return utente_id

    def utente_valido(self, email: str, password: str, nome: str, cognome: str, telefono: str,
                      ruolo: str = "cliente", riceve_prenotazioni: bool = False) -> Utente:
        """
        Controlla i dati di un nuovo utente e trasforma la password in hash, senza salvare niente.
        Usato anche da SaloniService, che crea salone e proprietario nella stessa transazione.
        Returns: l'Utente senza id e senza salone.
        Raises: DatiNonValidiError se un dato non è valido o il ruolo non esiste;
            EmailGiaRegistrataError se l'email è già usata.
        """
        if ruolo != "cliente" and ruolo not in RUOLI_STAFF:
            raise DatiNonValidiError("Il ruolo deve essere dipendente o proprietario.")
        email = testo_obbligatorio(email, "email", 255).lower()
        if "@" not in email:
            raise DatiNonValidiError("L'email non è valida.")
        if len(password) < LUNGHEZZA_MINIMA_PASSWORD:
            raise DatiNonValidiError(
                f"La password deve avere almeno {LUNGHEZZA_MINIMA_PASSWORD} caratteri."
            )
        nome = _nome_valido(nome, "nome")
        cognome = _nome_valido(cognome, "cognome")
        telefono = telefono_valido(telefono)

        if self._utenti.leggi_per_email(email) is not None:
            raise EmailGiaRegistrataError("Esiste già un account con questa email.")

        return Utente(
            email=email,
            password_hash=generate_password_hash(password),
            nome=nome,
            cognome=cognome,
            telefono=telefono,
            ruolo=ruolo,
            riceve_prenotazioni=riceve_prenotazioni,
        )

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
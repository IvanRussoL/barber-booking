from datetime import UTC, datetime, timedelta

from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError
from app.modelli.utente import Utente
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.utente import UtenteRepository
from app.servizi.auth import AuthService
from app.servizi.calendario import GIORNI_DA_CONTROLLARE
from app.servizi.disponibilita import in_utc


class PersonaleService:
    """
    I dipendenti di un salone visti dal proprietario: creazione, disattivazione e riattivazione.
    Il salone arriva dalla sessione del proprietario: un dipendente di un altro salone risulta non trovato.
    """

    def __init__(self, connessione, salone_id: int):
        self._conn = connessione
        self._salone_id = salone_id
        self._utenti = UtenteRepository(connessione)
        self._prenotazioni = PrenotazioneRepository(connessione)

    def crea_dipendente(self, email: str, password: str, nome: str, cognome: str, telefono: str) -> int:
        """
        Crea un dipendente del salone che riceve prenotazioni. La password è provvisoria: la sceglie
        il proprietario e la comunica al dipendente.
        Returns: l'id del nuovo utente.
        Raises: DatiNonValidiError, EmailGiaRegistrataError.
        """
        return AuthService(self._conn).crea_staff(
            email, password, nome, cognome, telefono, "dipendente", True, self._salone_id,
        )

    def disattivati(self) -> list[Utente]:
        """
        I dipendenti disattivati del salone, per poterli riattivare.
        """
        return self._utenti.elenca_dipendenti_disattivati(self._salone_id)

    def imposta_attivo(self, dipendente_id: int, attivo: bool, adesso: datetime | None = None) -> Utente:
        """
        Disattiva o riattiva un dipendente. Un dipendente disattivato non entra più nel sito e non
        riceve prenotazioni; la sua sessione si chiude alla richiesta successiva. Conferma con commit.
        Il proprietario non si disattiva da qui: la regola vale solo per il ruolo dipendente.
        Returns: il dipendente.
        Raises: RisorsaNonTrovataError se non è un dipendente di questo salone;
            DatiNonValidiError se ha ancora appuntamenti in programma.
        """
        adesso = adesso or datetime.now(UTC)
        dipendente = self._utenti.leggi_per_id(dipendente_id)
        if dipendente is None or dipendente.salone_id != self._salone_id or dipendente.ruolo != "dipendente":
            raise RisorsaNonTrovataError("Dipendente non trovato.")
        if not attivo:
            # Blocco della riga come durante una prenotazione: nessuno può prenotarlo mentre controllo.
            self._utenti.blocca(dipendente_id)
            futuri = self._prenotazioni.intervalli_occupati(
                dipendente_id, in_utc(adesso), in_utc(adesso + timedelta(days=GIORNI_DA_CONTROLLARE)), in_utc(adesso)
            )
            if futuri:
                raise DatiNonValidiError(
                    f"{dipendente.nome} ha ancora appuntamenti in programma: annullali prima dalla sua agenda."
                )
        self._utenti.imposta_attivo(dipendente_id, attivo)
        self._conn.commit()
        return dipendente

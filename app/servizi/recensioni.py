from datetime import UTC, datetime

from app.eccezioni import DatiNonValidiError, RecensioneNonConsentitaError, RisorsaNonTrovataError
from app.modelli.prenotazione import Prenotazione
from app.modelli.recensione import Recensione
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.recensione import RecensioneRepository
from app.servizi.disponibilita import in_utc
from app.servizi.validazione import testo_facoltativo

LUNGHEZZA_MASSIMA_COMMENTO = 500


def puo_recensire(prenotazione: Prenotazione, gia_recensita: bool, adesso: datetime) -> bool:
    """
    Un appuntamento si recensisce una volta sola, quando è stato confermato ed è già finito.
    """
    return prenotazione.stato == "confermata" and prenotazione.fine <= in_utc(adesso) and not gia_recensita


def voto_valido(valore: str) -> int:
    """
    Converte il voto del modulo: un intero da 1 a 5.
    Raises: DatiNonValidiError se non è valido.
    """
    valore = str(valore).strip()
    if valore not in {"1", "2", "3", "4", "5"}:
        raise DatiNonValidiError("Scegli un voto da 1 a 5 stelle.")
    return int(valore)


class RecensioniService:
    """
    Recensioni dei saloni: le lascia solo il cliente che ha avuto l'appuntamento, una per appuntamento.
    """

    def __init__(self, connessione):
        self._conn = connessione
        self._prenotazioni = PrenotazioneRepository(connessione)
        self._recensioni = RecensioneRepository(connessione)

    def prenotazione_da_recensire(self, prenotazione_id: int, cliente_id: int,
                                  adesso: datetime | None = None, per_aggiornamento: bool = False) -> Prenotazione:
        """
        Legge l'appuntamento che il cliente vuole recensire (solo se è suo) e controlla che si possa recensire.
        Returns: la Prenotazione.
        Raises: RisorsaNonTrovataError se non esiste o è di un altro cliente (404);
            RecensioneNonConsentitaError se non è ancora svolto, è annullato o è già recensito.
        """
        adesso = adesso or datetime.now(UTC)
        prenotazione = self._prenotazioni.leggi_per_id(
            prenotazione_id, cliente_id=cliente_id, per_aggiornamento=per_aggiornamento
        )
        if prenotazione is None:
            raise RisorsaNonTrovataError("Prenotazione non trovata.")
        gia_recensita = prenotazione.id in self._recensioni.prenotazioni_recensite(cliente_id)
        if not puo_recensire(prenotazione, gia_recensita, adesso):
            raise RecensioneNonConsentitaError(
                "Puoi recensire solo un appuntamento già svolto, una volta sola."
            )
        return prenotazione

    def crea(self, prenotazione_id: int, cliente_id: int, voto: str, commento: str,
             adesso: datetime | None = None) -> int:
        """
        Salva la recensione di un appuntamento svolto e conferma con commit. La riga della prenotazione
        è letta con FOR UPDATE: due invii ravvicinati non producono due recensioni (c'è anche il vincolo UNIQUE).
        Returns: l'id della recensione.
        Raises: RisorsaNonTrovataError, RecensioneNonConsentitaError, DatiNonValidiError.
        """
        prenotazione = self.prenotazione_da_recensire(prenotazione_id, cliente_id, adesso, per_aggiornamento=True)
        recensione = Recensione(
            prenotazione_id=prenotazione.id, salone_id=prenotazione.salone_id, cliente_id=cliente_id,
            voto=voto_valido(voto),
            commento=testo_facoltativo(commento, "commento", LUNGHEZZA_MASSIMA_COMMENTO),
        )
        recensione_id = self._recensioni.inserisci(recensione)
        self._conn.commit()
        return recensione_id

    def prenotazioni_recensite(self, cliente_id: int) -> set[int]:
        """
        Gli id delle prenotazioni del cliente già recensite.
        """
        return self._recensioni.prenotazioni_recensite(cliente_id)

    def del_salone(self, salone_id: int, limite: int = 10) -> tuple[float | None, int, list[Recensione]]:
        """
        Media, numero e ultime recensioni di un salone, per la sua pagina pubblica.
        Returns: (media o None, numero di recensioni, recensioni più recenti).
        """
        media, numero = self._recensioni.media(salone_id)
        return media, numero, self._recensioni.elenca_per_salone(salone_id, limite)

from datetime import UTC, date, datetime, time, timedelta

from app.eccezioni import DatiNonValidiError
from app.modelli.orario import EccezioneData, Turno
from app.repository.orario import OrarioRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.servizi.disponibilita import DisponibilitaService, in_utc
from app.servizi.validazione import testo_facoltativo


def _data_valida(valore: str, oggi: date) -> date:
    """
    Converte la data del modulo (AAAA-MM-GG); le date passate non si modificano.
    Raises: DatiNonValidiError se non è una data o è nel passato.
    """
    try:
        giorno = date.fromisoformat(valore)
    except (TypeError, ValueError):
        raise DatiNonValidiError("Scegli una data valida.")
    if giorno < oggi:
        raise DatiNonValidiError("Non si possono modificare gli orari di una data passata.")
    return giorno


def _ora_valida(valore: str) -> time:
    """
    Converte un orario HH:MM della griglia di 30 minuti.
    Raises: DatiNonValidiError se non è un orario o non cade su :00 o :30.
    """
    try:
        ora = time.fromisoformat(valore)
    except (TypeError, ValueError):
        raise DatiNonValidiError("Gli orari devono essere nel formato HH:MM.")
    if ora.minute not in (0, 30) or ora.second:
        raise DatiNonValidiError("Gli orari devono cadere sulla griglia di 30 minuti (es. 09:00 o 09:30).")
    return ora


def turni_validi(orari: list[tuple[str, str]]) -> list[Turno]:
    """
    Controlla i turni del modulo: il primo obbligatorio, il secondo facoltativo (entrambi i campi vuoti),
    inizio prima della fine, secondo turno dopo il primo.
    Returns: la lista dei Turni.
    Raises: DatiNonValidiError se un turno non è valido.
    """
    turni = []
    for numero, (inizio, fine) in enumerate(orari, start=1):
        if numero > 1 and not inizio.strip() and not fine.strip():
            continue
        turno = Turno(_ora_valida(inizio), _ora_valida(fine))
        if turno.ora_fine <= turno.ora_inizio:
            raise DatiNonValidiError(f"Nel turno {numero} l'orario di fine deve venire dopo quello di inizio.")
        if turni and turno.ora_inizio < turni[-1].ora_fine:
            raise DatiNonValidiError("Il secondo turno deve iniziare dopo la fine del primo.")
        turni.append(turno)
    return turni


class CalendarioService:
    """
    Orari delle singole date decisi dal proprietario: festività, chiusure e aperture straordinarie.
    Il calendario settimanale resta quello di partenza.
    """

    def __init__(self, connessione):
        self._conn = connessione
        self._disponibilita = DisponibilitaService(connessione)
        self._orari = OrarioRepository(connessione)
        self._prenotazioni = PrenotazioneRepository(connessione)

    @property
    def disponibilita(self) -> DisponibilitaService:
        return self._disponibilita

    def _oggi(self, adesso: datetime) -> date:
        return adesso.astimezone(self._disponibilita.fuso_orario).date()

    def _controlla_prenotazioni(self, giorno: date, turni: list[Turno], adesso: datetime) -> None:
        """
        Le prenotazioni già presenti in quella data devono stare tutte dentro i nuovi turni.
        Raises: DatiNonValidiError con il numero di prenotazioni che resterebbero fuori.
        """
        fuso = self._disponibilita.fuso_orario
        inizio_giorno = datetime.combine(giorno, time(0), fuso)
        intervalli = self._prenotazioni.intervalli_attivi_salone(
            in_utc(inizio_giorno), in_utc(inizio_giorno + timedelta(days=1)), in_utc(adesso)
        )
        turni_utc = [(in_utc(datetime.combine(giorno, t.ora_inizio, fuso)),
                      in_utc(datetime.combine(giorno, t.ora_fine, fuso))) for t in turni]
        fuori = sum(1 for inizio, fine in intervalli
                    if not any(t_inizio <= inizio and fine <= t_fine for t_inizio, t_fine in turni_utc))
        if fuori:
            quante = "c'è 1 prenotazione" if fuori == 1 else f"ci sono {fuori} prenotazioni"
            raise DatiNonValidiError(
                f"In questa data {quante} fuori dai nuovi orari: "
                "annullale prima dall'agenda del professionista, poi modifica gli orari."
            )

    def imposta_eccezione(self, data: str, aperto: str, orari: list[tuple[str, str]], nota: str,
                          adesso: datetime | None = None) -> date:
        """
        Decide l'orario di una data: chiuso, oppure aperto con uno o due turni. Conferma con commit.
        Returns: la data modificata.
        Raises: DatiNonValidiError se un dato non è valido o se resterebbero fuori prenotazioni già fatte.
        """
        adesso = adesso or datetime.now(UTC)
        giorno = _data_valida(data, self._oggi(adesso))
        if aperto not in ("si", "no"):
            raise DatiNonValidiError("Scegli se il salone è aperto o chiuso.")
        turni = turni_validi(orari) if aperto == "si" else []
        self._controlla_prenotazioni(giorno, turni, adesso)
        self._orari.salva_eccezione(EccezioneData(giorno, aperto == "si", turni, testo_facoltativo(nota, "nota", 255)))
        self._conn.commit()
        return giorno

    def rimuovi_eccezione(self, data: str, adesso: datetime | None = None) -> date:
        """
        Torna al calendario settimanale per una data (una festività torna "da definire"). Conferma con commit.
        Returns: la data modificata.
        Raises: DatiNonValidiError se la data non è valida o se resterebbero fuori prenotazioni già fatte.
        """
        adesso = adesso or datetime.now(UTC)
        giorno = _data_valida(data, self._oggi(adesso))
        self._controlla_prenotazioni(giorno, self._orari.turni_settimanali(giorno.isoweekday()), adesso)
        self._orari.elimina_eccezione(giorno)
        self._conn.commit()
        return giorno

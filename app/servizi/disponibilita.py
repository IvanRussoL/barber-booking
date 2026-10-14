import calendar
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError
from app.modelli.orario import Turno
from app.modelli.salone import Salone
from app.servizi.festivita import giornate_a_rischio
from app.repository.indisponibilita import IndisponibilitaRepository
from app.repository.orario import OrarioRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.salone import SaloneRepository

PASSO_GRIGLIA = timedelta(minutes=30)
GIORNI_BREVI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]


@dataclass
class GiornoSpeciale:
    """
    Data fuori dal calendario settimanale: giornata a rischio ancora da definire, oppure eccezione decisa.
    stato vale "da_definire", "chiuso" o "aperto" (con i turni dell'eccezione).
    """
    data: date
    stato: str
    turni: list[Turno] = field(default_factory=list)
    nota: str | None = None


def in_utc(momento: datetime) -> datetime:
    """
    Converte una data e ora con fuso orario nel formato salvato nel database: UTC senza fuso orario.
    """
    return momento.astimezone(UTC).replace(tzinfo=None)


def _si_sovrappone(inizio: datetime, fine: datetime, intervalli: list[tuple[datetime, datetime]]) -> bool:
    """
    Due intervalli si sovrappongono se ognuno inizia prima che l'altro finisca.
    """
    return any(inizio < fine_altro and fine > inizio_altro for inizio_altro, fine_altro in intervalli)


class DisponibilitaService:
    """
    Calendario di un salone: orari, stato di apertura e calcolo degli orari liberi di un professionista.
    """

    def __init__(self, connessione, salone_id: int):
        """
        Raises: RisorsaNonTrovataError se il salone non esiste.
        """
        self._salone = SaloneRepository(connessione).leggi_per_id(salone_id)
        if self._salone is None:
            raise RisorsaNonTrovataError("Salone non trovato.")
        self._fuso_orario = ZoneInfo(self._salone.fuso_orario)
        self._orari = OrarioRepository(connessione)
        self._indisponibilita = IndisponibilitaRepository(connessione)
        self._prenotazioni = PrenotazioneRepository(connessione)

    @property
    def salone(self) -> Salone:
        """
        Il salone di questo calendario.
        """
        return self._salone

    @property
    def fuso_orario(self) -> ZoneInfo:
        """
        Fuso orario del salone.
        """
        return self._fuso_orario

    def finestra(self, adesso: datetime) -> tuple[date, date]:
        """
        Date prenotabili: da oggi all'ultimo giorno del mese che viene mesi_prenotabili mesi dopo il corrente.
        Args: adesso, data e ora attuali con fuso orario.
        Returns: (primo giorno, ultimo giorno), nella data locale del salone.
        """
        oggi = adesso.astimezone(self._fuso_orario).date()
        anni, mese_zero = divmod(oggi.month - 1 + self._salone.mesi_prenotabili, 12)
        anno, mese = oggi.year + anni, mese_zero + 1
        return oggi, date(anno, mese, calendar.monthrange(anno, mese)[1])

    def turni_del_giorno(self, giorno: date) -> list[Turno]:
        """
        Turni di apertura di una data: quelli dell'eccezione se esiste, altrimenti quelli della settimana.
        Returns: la lista dei Turni, vuota se il salone è chiuso.
        """
        eccezione = self._orari.leggi_eccezione(self._salone.id, giorno)
        if eccezione is not None:
            return eccezione.turni if eccezione.aperto else []
        return self._orari.turni_settimanali(self._salone.id, giorno.isoweekday())

    def slot_liberi(self, dipendente_id: int, giorno: date, durata_minuti: int,
                    adesso: datetime, cliente_id: int | None = None) -> list[datetime]:
        """
        Orari di inizio in cui un appuntamento della durata indicata sta per intero in un turno,
        non è già passato e non si sovrappone a prenotazioni, assenze o chiusure.
        Il professionista deve appartenere a questo salone: lo controlla chi chiama (PrenotazioneService).
        Args: giorno nella data locale; adesso con fuso orario; cliente_id, se indicato,
            esclude anche gli orari in cui il cliente ha già un appuntamento con altri.
        Returns: gli orari di inizio con il fuso orario del salone, in ordine.
        Raises: DatiNonValidiError se il giorno è fuori dalla finestra di prenotazione.
        """
        primo, ultimo = self.finestra(adesso)
        if not primo <= giorno <= ultimo:
            raise DatiNonValidiError(
                f"Si può prenotare dal {primo:%d/%m/%Y} al {ultimo:%d/%m/%Y}."
            )
        turni = self.turni_del_giorno(giorno)
        if not turni:
            return []

        durata = timedelta(minutes=durata_minuti)
        apertura = datetime.combine(giorno, turni[0].ora_inizio, self._fuso_orario)
        chiusura = datetime.combine(giorno, turni[-1].ora_fine, self._fuso_orario)
        occupati = self._prenotazioni.intervalli_occupati(
            dipendente_id, in_utc(apertura), in_utc(chiusura), in_utc(adesso)
        ) + self._indisponibilita.periodi_sovrapposti(
            self._salone.id, dipendente_id, in_utc(apertura), in_utc(chiusura)
        )
        if cliente_id is not None:
            occupati += self._prenotazioni.intervalli_occupati_cliente(
                cliente_id, in_utc(apertura), in_utc(chiusura), in_utc(adesso)
            )

        liberi = []
        for turno in turni:
            inizio = datetime.combine(giorno, turno.ora_inizio, self._fuso_orario)
            fine_turno = datetime.combine(giorno, turno.ora_fine, self._fuso_orario)
            while inizio + durata <= fine_turno:
                if inizio > adesso and not _si_sovrappone(in_utc(inizio), in_utc(inizio + durata), occupati):
                    liberi.append(inizio)
                inizio += PASSO_GRIGLIA
        return liberi

    def orario_settimanale(self) -> list[tuple[int, list[Turno]]]:
        """
        Calendario settimanale del salone, per la pagina pubblica.
        Returns: sette coppie (giorno da 1 a 7, turni), con la lista vuota nei giorni di chiusura.
        """
        return [(giorno, self._orari.turni_settimanali(self._salone.id, giorno)) for giorno in range(1, 8)]

    def stato_apertura(self, adesso: datetime) -> tuple[bool, str]:
        """
        Dice se il salone è aperto in questo momento (eccezioni per data comprese) e quando chiude o riapre.
        Args: adesso con fuso orario.
        Returns: (aperto, testo da mostrare), es. (True, "Aperto ora · chiude alle 13:00").
        """
        locale = adesso.astimezone(self._fuso_orario)
        for giorni_dopo in range(8):
            giorno = locale.date() + timedelta(days=giorni_dopo)
            for turno in self.turni_del_giorno(giorno):
                inizio = datetime.combine(giorno, turno.ora_inizio, self._fuso_orario)
                fine = datetime.combine(giorno, turno.ora_fine, self._fuso_orario)
                if inizio <= locale < fine:
                    return True, f"Aperto ora · chiude alle {fine:%H:%M}"
                if locale < inizio:
                    if giorni_dopo == 0:
                        quando = "oggi"
                    elif giorni_dopo == 1:
                        quando = "domani"
                    else:
                        quando = GIORNI_BREVI[giorno.weekday()]
                    return False, f"Chiuso ora · riapre {quando} alle {inizio:%H:%M}"
        return False, "Chiuso"

    def da_definire(self, giorno: date) -> bool:
        """
        Vero se la data è una giornata a rischio (festività, vigilia), il salone di solito è aperto
        quel giorno della settimana e il proprietario non ha ancora deciso l'orario.
        """
        return (giorno in giornate_a_rischio(giorno.year)
                and self._orari.leggi_eccezione(self._salone.id, giorno) is None
                and bool(self._orari.turni_settimanali(self._salone.id, giorno.isoweekday())))

    def giornate_speciali(self, da: date, a: date) -> list[GiornoSpeciale]:
        """
        Date in [da, a] con un'eccezione decisa dal proprietario o ancora da definire, in ordine di data.
        Returns: la lista dei GiornoSpeciale.
        """
        speciali = {
            eccezione.data: GiornoSpeciale(eccezione.data, "aperto" if eccezione.aperto else "chiuso",
                                           eccezione.turni, eccezione.nota)
            for eccezione in self._orari.elenca_eccezioni(self._salone.id, da, a)
        }
        for anno in range(da.year, a.year + 1):
            for giorno in giornate_a_rischio(anno):
                if (da <= giorno <= a and giorno not in speciali
                        and self._orari.turni_settimanali(self._salone.id, giorno.isoweekday())):
                    speciali[giorno] = GiornoSpeciale(giorno, "da_definire")
        return [speciali[giorno] for giorno in sorted(speciali)]


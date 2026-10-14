from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.eccezioni import DatiNonValidiError, RisorsaNonTrovataError
from app.modelli.indisponibilita import Indisponibilita
from app.repository.indisponibilita import IndisponibilitaRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.utente import UtenteRepository
from app.servizi.disponibilita import DisponibilitaService, in_utc
from app.servizi.validazione import testo_facoltativo

# Un periodo lungo al massimo un anno: basta per ferie, malattie e lavori di ristrutturazione.
GIORNI_MASSIMI = 366


@dataclass
class Periodo:
    """
    Un'assenza o una chiusura come la vede il proprietario: giorni in ora locale e chi riguarda.
    """
    id: int
    dal: date
    al: date
    chi: str
    nota: str | None


class AssenzeService:
    """
    Assenze dei professionisti e chiusure dell'intero salone, a giorni interi. Nei giorni indicati
    il calcolo degli slot non propone orari (la regola è già in DisponibilitaService).
    """

    def __init__(self, connessione, salone_id: int):
        self._conn = connessione
        self._salone_id = salone_id
        self._disponibilita = DisponibilitaService(connessione, salone_id)
        self._periodi = IndisponibilitaRepository(connessione)
        self._prenotazioni = PrenotazioneRepository(connessione)
        self._utenti = UtenteRepository(connessione)

    def professionisti(self):
        """
        Le persone del salone che ricevono prenotazioni, per il menu "Chi".
        """
        return self._utenti.elenca_professionisti(self._salone_id)

    def elenca(self, adesso: datetime | None = None) -> list[Periodo]:
        """
        Assenze e chiusure in corso o future, in ordine di inizio.
        Returns: la lista dei Periodi, con i giorni nell'ora locale del salone.
        """
        adesso = adesso or datetime.now(UTC)
        fuso = self._disponibilita.fuso_orario
        nomi = {u.id: f"{u.nome} {u.cognome}" for u in self._utenti.elenca_professionisti(self._salone_id)}
        periodi = []
        for periodo in self._periodi.elenca_dal(self._salone_id, in_utc(adesso)):
            dal = periodo.inizio.replace(tzinfo=UTC).astimezone(fuso).date()
            # La fine è la mezzanotte del giorno dopo l'ultimo: il giorno prima è l'ultimo giorno del periodo.
            al = (periodo.fine.replace(tzinfo=UTC).astimezone(fuso) - timedelta(seconds=1)).date()
            chi = "Tutto il salone" if periodo.dipendente_id is None else nomi.get(periodo.dipendente_id, "Professionista non più attivo")
            periodi.append(Periodo(periodo.id, dal, al, chi, periodo.nota))
        return periodi

    def aggiungi(self, chi: str, dal: str, al: str, nota: str, adesso: datetime | None = None) -> None:
        """
        Aggiunge un'assenza di un professionista (chi = il suo id) o una chiusura del salone (chi vuoto),
        dal primo all'ultimo giorno compresi. Conferma con commit.
        Raises: DatiNonValidiError se un dato non è valido o se nel periodo ci sono prenotazioni.
        """
        adesso = adesso or datetime.now(UTC)
        fuso = self._disponibilita.fuso_orario
        primo, ultimo = self._giorni_validi(dal, al, adesso.astimezone(fuso).date())
        professionisti = self._utenti.elenca_professionisti(self._salone_id)
        if chi:
            # Solo un professionista attivo di questo salone: un id di un altro salone non è nell'elenco.
            scelto = next((u for u in professionisti if str(u.id) == chi), None)
            if scelto is None:
                raise DatiNonValidiError("Scegli un professionista dall'elenco.")
            coinvolti = [scelto]
        else:
            coinvolti = professionisti
        inizio = in_utc(datetime.combine(primo, time(0), fuso))
        fine = in_utc(datetime.combine(ultimo + timedelta(days=1), time(0), fuso))
        # Blocco dei professionisti coinvolti, come durante una prenotazione: una prenotazione
        # in corso per loro aspetta la fine di questa transazione e poi vede il nuovo periodo.
        for utente in coinvolti:
            self._utenti.blocca(utente.id)
        if chi:
            occupati = self._prenotazioni.intervalli_occupati(scelto.id, inizio, fine, in_utc(adesso))
        else:
            occupati = self._prenotazioni.intervalli_attivi_salone(self._salone_id, inizio, fine, in_utc(adesso))
        if occupati:
            quante = "c'è 1 prenotazione" if len(occupati) == 1 else f"ci sono {len(occupati)} prenotazioni"
            raise DatiNonValidiError(
                f"Nel periodo scelto {quante}: annullale prima dall'agenda del professionista."
            )
        self._periodi.inserisci(Indisponibilita(
            inizio=inizio, fine=fine, salone_id=self._salone_id,
            dipendente_id=scelto.id if chi else None, nota=testo_facoltativo(nota, "nota", 255),
        ))
        self._conn.commit()

    def elimina(self, periodo_id: int) -> None:
        """
        Toglie un'assenza o una chiusura del salone. Conferma con commit.
        Raises: RisorsaNonTrovataError se non esiste o è di un altro salone.
        """
        if not self._periodi.elimina(self._salone_id, periodo_id):
            raise RisorsaNonTrovataError("Periodo non trovato.")
        self._conn.commit()

    @staticmethod
    def _giorni_validi(dal: str, al: str, oggi: date) -> tuple[date, date]:
        """
        Converte primo e ultimo giorno del modulo (AAAA-MM-GG).
        Raises: DatiNonValidiError se non sono date, il primo è passato, l'ultimo viene prima del primo
            o il periodo supera GIORNI_MASSIMI.
        """
        try:
            primo, ultimo = date.fromisoformat(dal), date.fromisoformat(al or dal)
        except (TypeError, ValueError):
            raise DatiNonValidiError("Scegli date valide.")
        if primo < oggi:
            raise DatiNonValidiError("Il periodo non può iniziare in una data passata.")
        if ultimo < primo:
            raise DatiNonValidiError("L'ultimo giorno deve venire dopo il primo.")
        if (ultimo - primo).days >= GIORNI_MASSIMI:
            raise DatiNonValidiError(f"Il periodo può durare al massimo {GIORNI_MASSIMI} giorni.")
        return primo, ultimo

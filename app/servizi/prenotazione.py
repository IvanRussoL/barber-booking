from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.eccezioni import (AnnullamentoNonConsentitoError, DatiNonValidiError, RisorsaNonTrovataError,
                           SlotNonDisponibileError)
from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.pagamenti.provider import PaymentProvider
from app.repository.impostazioni import ImpostazioniRepository
from app.repository.pagamento import PagamentoRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository
from app.servizi.disponibilita import DisponibilitaService, in_utc

MINUTI_PER_PAGARE = 30
ORE_MINIME_PER_ANNULLARE = 2
MODALITA_PAGAMENTO = ("acconto", "completo")


@dataclass
class RigaStorico:
    """
    Una prenotazione come la vede il cliente nella sua area: con professionista, pagato e annullabilità.
    """
    prenotazione: Prenotazione
    professionista: str
    pagato_centesimi: int
    annullabile: bool


@dataclass
class Appuntamento:
    """
    Una prenotazione nell'agenda del professionista, con i recapiti del cliente.
    """
    prenotazione: Prenotazione
    cliente: Utente


def calcola_acconto(totale_centesimi: int, percentuale: int) -> int:
    """
    Acconto arrotondato al centesimo più vicino (le metà per eccesso), almeno 1 centesimo.
    """
    return max(1, (totale_centesimi * percentuale + 50) // 100)


def _intero(valore: str, campo: str) -> int:
    """
    Converte un id ricevuto dal modulo in intero.
    Raises: DatiNonValidiError se non è un numero intero positivo.
    """
    if not str(valore).strip().isdigit():
        raise DatiNonValidiError(f"Scegli {campo}.")
    return int(valore)


class PrenotazioneService:
    """
    Creazione delle prenotazioni e gestione del loro pagamento.
    """

    def __init__(self, connessione, provider: PaymentProvider):
        self._conn = connessione
        self._provider = provider
        self._disponibilita = DisponibilitaService(connessione)
        self._prenotazioni = PrenotazioneRepository(connessione)
        self._pagamenti = PagamentoRepository(connessione)
        self._servizi = ServizioRepository(connessione)
        self._utenti = UtenteRepository(connessione)

    @property
    def disponibilita(self) -> DisponibilitaService:
        """
        Il servizio di calcolo degli slot, con la stessa connessione.
        """
        return self._disponibilita

    def servizi_scelti(self, servizi_ids: list[str]) -> list[Servizio]:
        """
        Controlla i servizi scelti dal cliente: almeno uno, esistenti e attivi, senza ripetizioni.
        Returns: la lista dei Servizi.
        Raises: DatiNonValidiError se la scelta non è valida.
        """
        ids = {_intero(valore, "un servizio valido") for valore in servizi_ids}
        if not ids:
            raise DatiNonValidiError("Scegli almeno un servizio.")
        servizi = [self._servizi.leggi_per_id(servizio_id) for servizio_id in sorted(ids)]
        if any(s is None or not s.attivo for s in servizi):
            raise DatiNonValidiError("Uno dei servizi scelti non è più disponibile.")
        return servizi

    def professionista(self, dipendente_id: str) -> Utente:
        """
        Controlla il professionista scelto: deve esistere, essere attivo e ricevere prenotazioni.
        Returns: l'Utente.
        Raises: DatiNonValidiError se non è prenotabile.
        """
        dipendente = self._utenti.leggi_per_id(_intero(dipendente_id, "un professionista"))
        if dipendente is None or not dipendente.attivo or not dipendente.riceve_prenotazioni:
            raise DatiNonValidiError("Il professionista scelto non è prenotabile.")
        return dipendente

    def slot_per_scelta(self, dipendente_id: str, servizi_ids: list[str], giorno: str,
                        adesso: datetime | None = None) -> list[datetime]:
        """
        Orari liberi per la scelta del modulo (usato dalla richiesta fetch della pagina di prenotazione).
        Returns: gli orari di inizio con il fuso orario del salone.
        Raises: DatiNonValidiError se servizi, professionista o data non sono validi.
        """
        adesso = adesso or datetime.now(UTC)
        servizi = self.servizi_scelti(servizi_ids)
        dipendente = self.professionista(dipendente_id)
        return self._disponibilita.slot_liberi(
            dipendente.id, _data(giorno), sum(s.durata_minuti for s in servizi), adesso
        )

    def crea(self, cliente: Utente, dipendente_id: str, servizi_ids: list[str], giorno: str,
             ora: str, modalita: str, adesso: datetime | None = None) -> tuple[int, str]:
        """
        Crea una prenotazione in attesa di pagamento e apre il pagamento, in un'unica transazione.
        Il SELECT ... FOR UPDATE sul dipendente mette in fila le richieste per lo stesso professionista:
        lo slot si ricontrolla solo dopo aver ottenuto il blocco, quindi due clienti non possono prenderlo insieme.
        Returns: (id della prenotazione, pagina di pagamento).
        Raises: DatiNonValidiError se un dato non è valido; SlotNonDisponibileError se l'orario non è libero.
        """
        adesso = adesso or datetime.now(UTC)
        if cliente.ruolo != "cliente":
            raise DatiNonValidiError("Solo i clienti possono prenotare.")
        if modalita not in MODALITA_PAGAMENTO:
            raise DatiNonValidiError("Scegli se pagare l'acconto o l'importo completo.")
        servizi = self.servizi_scelti(servizi_ids)
        dipendente = self.professionista(dipendente_id)
        durata = sum(s.durata_minuti for s in servizi)
        inizio = datetime.combine(_data(giorno), _ora(ora), self._disponibilita.fuso_orario)

        self._prenotazioni.segna_scadute(in_utc(adesso))
        self._utenti.blocca(dipendente.id)
        if inizio not in self._disponibilita.slot_liberi(dipendente.id, inizio.date(), durata, adesso):
            raise SlotNonDisponibileError("L'orario scelto non è più disponibile: scegline un altro.")

        prenotazione = Prenotazione(
            cliente_id=cliente.id,
            dipendente_id=dipendente.id,
            inizio=in_utc(inizio),
            fine=in_utc(inizio + timedelta(minutes=durata)),
            modalita_pagamento=modalita,
            scade_il=in_utc(adesso + timedelta(minutes=MINUTI_PER_PAGARE)),
            servizi=[ServizioPrenotato(s.id, s.nome, s.durata_minuti, s.prezzo_centesimi) for s in servizi],
        )
        prenotazione_id = self._prenotazioni.inserisci(prenotazione)

        importo = prenotazione.prezzo_totale()
        if modalita == "acconto":
            percentuale = ImpostazioniRepository(self._conn).leggi().percentuale_acconto
            importo = calcola_acconto(importo, percentuale)
        sessione = self._provider.crea_sessione(importo, f"Prenotazione n. {prenotazione_id}")
        self._pagamenti.inserisci(Pagamento(
            tipo="online", importo_centesimi=importo, prenotazione_id=prenotazione_id,
            riferimento_provider=sessione.riferimento,
        ))
        self._conn.commit()
        return prenotazione_id, sessione.url

    def pagamento_del_cliente(self, riferimento: str, cliente_id: int) -> tuple[Pagamento, Prenotazione]:
        """
        Legge un pagamento con la sua prenotazione, solo se appartiene al cliente.
        Returns: (Pagamento, Prenotazione).
        Raises: RisorsaNonTrovataError se non esiste o è di un altro cliente (stessa risposta).
        """
        pagamento = self._pagamenti.leggi_per_riferimento(riferimento)
        prenotazione = None
        if pagamento is not None and pagamento.prenotazione_id is not None:
            prenotazione = self._prenotazioni.leggi_per_id(pagamento.prenotazione_id)
        if prenotazione is None or prenotazione.cliente_id != cliente_id:
            raise RisorsaNonTrovataError("Pagamento non trovato.")
        return pagamento, prenotazione

    def conferma_pagamento(self, riferimento: str, adesso: datetime | None = None) -> bool:
        """
        Registra un pagamento eseguito (con Stripe lo chiamerebbe il webhook). Idempotente:
        una seconda notifica dello stesso pagamento non ha effetti. Se la prenotazione è già
        scaduta o annullata, il pagamento viene rimborsato e la prenotazione non viene confermata.
        Returns: True se la prenotazione è confermata.
        Raises: RisorsaNonTrovataError se il riferimento non esiste.
        """
        adesso = adesso or datetime.now(UTC)
        pagamento = self._pagamenti.leggi_per_riferimento(riferimento, per_aggiornamento=True)
        if pagamento is None:
            raise RisorsaNonTrovataError("Pagamento non trovato.")
        prenotazione = self._prenotazioni.leggi_per_id(pagamento.prenotazione_id)
        if pagamento.stato == "completato":
            self._conn.commit()  # niente da salvare: chiude la transazione e libera il blocco
            return prenotazione.stato == "confermata"

        self._pagamenti.aggiorna_stato(pagamento.id, "completato")
        ancora_valida = prenotazione.stato == "in_attesa_pagamento" and prenotazione.scade_il > in_utc(adesso)
        if ancora_valida:
            self._prenotazioni.aggiorna_stato(prenotazione.id, "confermata")
        else:
            if prenotazione.stato == "in_attesa_pagamento":
                self._prenotazioni.aggiorna_stato(prenotazione.id, "scaduta")
            riferimento_rimborso = self._provider.rimborsa(riferimento, pagamento.importo_centesimi)
            self._pagamenti.inserisci(Pagamento(
                tipo="rimborso", importo_centesimi=pagamento.importo_centesimi,
                prenotazione_id=prenotazione.id, stato="completato",
                riferimento_provider=riferimento_rimborso,
            ))
        self._conn.commit()
        return ancora_valida

    def annulla_pagamento(self, riferimento: str, adesso: datetime | None = None) -> None:
        """
        Il cliente esce dalla pagina di pagamento: la sessione si chiude, la prenotazione
        in attesa viene annullata e lo slot torna libero subito.
        Raises: RisorsaNonTrovataError se il riferimento non esiste.
        """
        adesso = adesso or datetime.now(UTC)
        pagamento = self._pagamenti.leggi_per_riferimento(riferimento, per_aggiornamento=True)
        if pagamento is None:
            raise RisorsaNonTrovataError("Pagamento non trovato.")
        if pagamento.stato != "in_attesa":
            self._conn.commit()  # niente da salvare: chiude la transazione e libera il blocco
            return
        prenotazione = self._prenotazioni.leggi_per_id(pagamento.prenotazione_id)
        self._provider.chiudi_sessione(riferimento)
        self._pagamenti.aggiorna_stato(pagamento.id, "fallito")
        if prenotazione.stato == "in_attesa_pagamento":
            self._prenotazioni.aggiorna_stato(prenotazione.id, "annullata", in_utc(adesso), "cliente")
        self._conn.commit()

    # --- Area cliente e agenda ---

    def puo_annullare(self, prenotazione: Prenotazione, adesso: datetime) -> bool:
        """
        Il cliente annulla solo prenotazioni confermate, fino a 2 ore prima dell'inizio.
        """
        mancano = prenotazione.inizio - in_utc(adesso)
        return prenotazione.stato == "confermata" and mancano >= timedelta(hours=ORE_MINIME_PER_ANNULLARE)

    def storico_cliente(self, cliente_id: int, adesso: datetime | None = None) -> list[RigaStorico]:
        """
        Prenotazioni del cliente con professionista, importo pagato e possibilità di annullare.
        Returns: la lista delle RigaStorico, dalla più recente.
        """
        adesso = adesso or datetime.now(UTC)
        righe = []
        for prenotazione in self._prenotazioni.elenca_per_cliente(cliente_id):
            dipendente = self._utenti.leggi_per_id(prenotazione.dipendente_id)
            righe.append(RigaStorico(
                prenotazione=prenotazione,
                professionista=f"{dipendente.nome} {dipendente.cognome}",
                pagato_centesimi=self._pagamenti.totale_pagato(prenotazione.id),
                annullabile=self.puo_annullare(prenotazione, adesso),
            ))
        return righe

    def prenotazione_del_cliente(self, prenotazione_id: int, cliente_id: int) -> Prenotazione:
        """
        Legge una prenotazione solo se appartiene al cliente (controllo dentro la query).
        Returns: la Prenotazione.
        Raises: RisorsaNonTrovataError se non esiste o è di un altro cliente (stessa risposta: 404).
        """
        prenotazione = self._prenotazioni.leggi_per_id(prenotazione_id, cliente_id=cliente_id)
        if prenotazione is None:
            raise RisorsaNonTrovataError("Prenotazione non trovata.")
        return prenotazione

    def annulla_dal_cliente(self, prenotazione_id: int, cliente_id: int, adesso: datetime | None = None) -> int:
        """
        Annulla una prenotazione del cliente e rimborsa esattamente quanto pagato online.
        La riga è letta con FOR UPDATE: due clic ravvicinati non producono due rimborsi.
        Returns: l'importo rimborsato in centesimi.
        Raises: RisorsaNonTrovataError se non è sua; AnnullamentoNonConsentitoError se non è annullabile.
        """
        adesso = adesso or datetime.now(UTC)
        prenotazione = self._prenotazioni.leggi_per_id(prenotazione_id, cliente_id=cliente_id, per_aggiornamento=True)
        if prenotazione is None:
            raise RisorsaNonTrovataError("Prenotazione non trovata.")
        if not self.puo_annullare(prenotazione, adesso):
            raise AnnullamentoNonConsentitoError(
                f"Si possono annullare solo le prenotazioni confermate, fino a "
                f"{ORE_MINIME_PER_ANNULLARE} ore prima dell'appuntamento."
            )
        rimborsato = 0
        for pagamento in self._pagamenti.online_completati(prenotazione.id):
            riferimento_rimborso = self._provider.rimborsa(pagamento.riferimento_provider, pagamento.importo_centesimi)
            self._pagamenti.inserisci(Pagamento(
                tipo="rimborso", importo_centesimi=pagamento.importo_centesimi,
                prenotazione_id=prenotazione.id, stato="completato",
                riferimento_provider=riferimento_rimborso,
            ))
            rimborsato += pagamento.importo_centesimi
        self._prenotazioni.aggiorna_stato(prenotazione.id, "annullata", in_utc(adesso), "cliente")
        self._conn.commit()
        return rimborsato

    def agenda(self, dipendente_id: int, adesso: datetime | None = None) -> list[Appuntamento]:
        """
        Prossimi appuntamenti confermati di un professionista, dall'inizio di oggi (ora locale).
        Returns: la lista degli Appuntamenti in ordine di inizio.
        """
        adesso = adesso or datetime.now(UTC)
        inizio_oggi = datetime.combine(
            adesso.astimezone(self._disponibilita.fuso_orario).date(), time(0), self._disponibilita.fuso_orario
        )
        return [
            Appuntamento(prenotazione, self._utenti.leggi_per_id(prenotazione.cliente_id))
            for prenotazione in self._prenotazioni.elenca_per_dipendente(dipendente_id, in_utc(inizio_oggi))
        ]


def _data(valore: str) -> date:
    """
    Converte la data del modulo (AAAA-MM-GG).
    Raises: DatiNonValidiError se non è una data valida.
    """
    try:
        return date.fromisoformat(valore)
    except (TypeError, ValueError):
        raise DatiNonValidiError("Scegli una data valida.")


def _ora(valore: str) -> time:
    """
    Converte l'orario scelto (HH:MM).
    Raises: DatiNonValidiError se non è un orario valido.
    """
    try:
        return time.fromisoformat(valore)
    except (TypeError, ValueError):
        raise DatiNonValidiError("Scegli un orario tra quelli liberi.")

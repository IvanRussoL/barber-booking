from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.eccezioni import (AnnullamentoNonConsentitoError, DatiNonValidiError, RisorsaNonTrovataError,
                           SlotNonDisponibileError)
from app.modelli.pagamento import Pagamento
from app.modelli.prenotazione import Prenotazione, ServizioPrenotato
from app.modelli.salone import Salone
from app.modelli.servizio import Servizio
from app.modelli.utente import Utente
from app.pagamenti.provider import PaymentProvider
from app.repository.pagamento import PagamentoRepository
from app.repository.recensione import RecensioneRepository
from app.repository.prenotazione import PrenotazioneRepository
from app.repository.salone import SaloneRepository
from app.repository.servizio import ServizioRepository
from app.repository.utente import UtenteRepository
from app.servizi.disponibilita import DisponibilitaService, in_utc
from app.servizi.recensioni import puo_recensire

MINUTI_PER_PAGARE = 30
ORE_MINIME_PER_ANNULLARE = 2
MODALITA_PAGAMENTO = ("acconto", "completo")


@dataclass
class RigaStorico:
    """
    Una prenotazione come la vede il cliente nella sua area: con salone, professionista, pagato
    e annullabilità. Il salone serve anche a mostrare l'orario nel suo fuso orario.
    """
    prenotazione: Prenotazione
    salone: Salone
    professionista: str
    pagato_centesimi: int
    annullabile: bool
    recensibile: bool = False  # appuntamento svolto e non ancora recensito


@dataclass
class Appuntamento:
    """
    Una prenotazione nell'agenda del professionista, con i recapiti del cliente
    e l'indicazione se il salone può ancora annullarla.
    """
    prenotazione: Prenotazione
    cliente: Utente
    annullabile: bool = False


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
    Creazione delle prenotazioni e gestione del loro pagamento, in qualsiasi salone.
    Il salone arriva dalla pagina del salone scelto (prenotazione) o dalla sessione (staff):
    servizi e professionisti di un altro salone vengono rifiutati.
    """

    def __init__(self, connessione, provider: PaymentProvider):
        self._conn = connessione
        self._provider = provider
        self._calendari: dict[int, DisponibilitaService] = {}
        self._prenotazioni = PrenotazioneRepository(connessione)
        self._pagamenti = PagamentoRepository(connessione)
        self._saloni = SaloneRepository(connessione)
        self._servizi = ServizioRepository(connessione)
        self._utenti = UtenteRepository(connessione)

    def disponibilita(self, salone_id: int) -> DisponibilitaService:
        """
        Il calendario di un salone, con la stessa connessione (creato una volta sola per salone).
        Raises: RisorsaNonTrovataError se il salone non esiste.
        """
        if salone_id not in self._calendari:
            self._calendari[salone_id] = DisponibilitaService(self._conn, salone_id)
        return self._calendari[salone_id]

    def salone_prenotabile(self, salone_id: int) -> Salone:
        """
        Il salone in cui il cliente vuole prenotare: deve esistere ed essere attivo.
        Returns: il Salone.
        Raises: RisorsaNonTrovataError se non esiste o è disattivato (stessa risposta: 404).
        """
        salone = self._saloni.leggi_per_id(salone_id)
        if salone is None or not salone.attivo:
            raise RisorsaNonTrovataError("Salone non trovato.")
        return salone

    def servizi_scelti(self, salone_id: int, servizi_ids: list[str]) -> list[Servizio]:
        """
        Controlla i servizi scelti dal cliente: almeno uno, del salone, esistenti e attivi, senza ripetizioni.
        Returns: la lista dei Servizi.
        Raises: DatiNonValidiError se la scelta non è valida (anche con un servizio di un altro salone).
        """
        ids = {_intero(valore, "un servizio valido") for valore in servizi_ids}
        if not ids:
            raise DatiNonValidiError("Scegli almeno un servizio.")
        servizi = [self._servizi.leggi_per_id(salone_id, servizio_id) for servizio_id in sorted(ids)]
        if any(s is None or not s.attivo for s in servizi):
            raise DatiNonValidiError("Uno dei servizi scelti non è più disponibile.")
        return servizi

    def professionista(self, salone_id: int, dipendente_id: str) -> Utente:
        """
        Controlla il professionista scelto: deve lavorare in questo salone, essere attivo e ricevere prenotazioni.
        Returns: l'Utente.
        Raises: DatiNonValidiError se non è prenotabile in questo salone.
        """
        dipendente = self._utenti.leggi_per_id(_intero(dipendente_id, "un professionista"))
        if (dipendente is None or dipendente.salone_id != salone_id
                or not dipendente.attivo or not dipendente.riceve_prenotazioni):
            raise DatiNonValidiError("Il professionista scelto non è prenotabile.")
        return dipendente

    def slot_per_scelta(self, salone_id: int, dipendente_id: str, servizi_ids: list[str], giorno: str,
                        adesso: datetime | None = None, cliente_id: int | None = None) -> list[datetime]:
        """
        Orari liberi per la scelta del modulo (usato dalla richiesta fetch della pagina di prenotazione),
        senza quelli in cui il cliente ha già un altro appuntamento, in qualsiasi salone.
        Returns: gli orari di inizio con il fuso orario del salone.
        Raises: RisorsaNonTrovataError se il salone non è prenotabile;
            DatiNonValidiError se servizi, professionista o data non sono validi.
        """
        adesso = adesso or datetime.now(UTC)
        self.salone_prenotabile(salone_id)
        servizi = self.servizi_scelti(salone_id, servizi_ids)
        dipendente = self.professionista(salone_id, dipendente_id)
        return self.disponibilita(salone_id).slot_liberi(
            dipendente.id, _data(giorno), sum(s.durata_minuti for s in servizi), adesso, cliente_id
        )

    def crea(self, cliente: Utente, salone_id: int, dipendente_id: str, servizi_ids: list[str], giorno: str,
             ora: str, modalita: str, adesso: datetime | None = None) -> tuple[int, str]:
        """
        Crea una prenotazione in attesa di pagamento e apre il pagamento, in un'unica transazione.
        Il SELECT ... FOR UPDATE sul cliente e poi sul dipendente mette in fila le richieste dello stesso
        cliente e quelle per lo stesso professionista: lo slot si ricontrolla solo dopo aver ottenuto i blocchi,
        quindi due richieste non possono prenderlo insieme. L'ordine fisso (prima il cliente) evita stalli.
        Returns: (id della prenotazione, pagina di pagamento).
        Raises: RisorsaNonTrovataError se il salone non è prenotabile; DatiNonValidiError se un dato
            non è valido; SlotNonDisponibileError se l'orario non è libero.
        """
        adesso = adesso or datetime.now(UTC)
        if cliente.ruolo != "cliente":
            raise DatiNonValidiError("Solo i clienti possono prenotare.")
        salone = self.salone_prenotabile(salone_id)
        if modalita not in MODALITA_PAGAMENTO:
            raise DatiNonValidiError("Scegli se pagare l'acconto o l'importo completo.")
        servizi = self.servizi_scelti(salone.id, servizi_ids)
        dipendente = self.professionista(salone.id, dipendente_id)
        durata = sum(s.durata_minuti for s in servizi)
        disponibilita = self.disponibilita(salone.id)
        inizio = datetime.combine(_data(giorno), _ora(ora), disponibilita.fuso_orario)

        self._prenotazioni.segna_scadute(in_utc(adesso))
        self._utenti.blocca(cliente.id)
        self._utenti.blocca(dipendente.id)
        if inizio not in disponibilita.slot_liberi(dipendente.id, inizio.date(), durata, adesso, cliente.id):
            raise SlotNonDisponibileError(
                "L'orario scelto non è più disponibile, oppure hai già un appuntamento a quell'ora: scegline un altro."
            )

        prenotazione = Prenotazione(
            salone_id=salone.id,
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
            importo = calcola_acconto(importo, salone.percentuale_acconto)
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
        Prenotazioni del cliente in tutti i saloni, con salone, professionista, importo pagato
        e possibilità di annullare o di recensire.
        Returns: la lista delle RigaStorico, dalla più recente.
        """
        adesso = adesso or datetime.now(UTC)
        recensite = RecensioneRepository(self._conn).prenotazioni_recensite(cliente_id)
        righe = []
        for prenotazione in self._prenotazioni.elenca_per_cliente(cliente_id):
            dipendente = self._utenti.leggi_per_id(prenotazione.dipendente_id)
            righe.append(RigaStorico(
                prenotazione=prenotazione,
                salone=self.disponibilita(prenotazione.salone_id).salone,
                professionista=f"{dipendente.nome} {dipendente.cognome}",
                pagato_centesimi=self._pagamenti.totale_pagato(prenotazione.id),
                annullabile=self.puo_annullare(prenotazione, adesso),
                recensibile=puo_recensire(prenotazione, prenotazione.id in recensite, adesso),
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
        return self._annulla_con_rimborso(prenotazione, "cliente", adesso)

    def _annulla_con_rimborso(self, prenotazione: Prenotazione, annullata_da: str, adesso: datetime) -> int:
        """
        Rimborsa ogni pagamento online riuscito, segna la prenotazione come annullata e conferma con commit.
        Usato sia dal cliente sia dal salone: la regola "rimborso pari a quanto pagato" è in un punto solo.
        Returns: l'importo rimborsato in centesimi.
        """
        rimborsato = 0
        for pagamento in self._pagamenti.online_completati(prenotazione.id):
            riferimento_rimborso = self._provider.rimborsa(pagamento.riferimento_provider, pagamento.importo_centesimi)
            self._pagamenti.inserisci(Pagamento(
                tipo="rimborso", importo_centesimi=pagamento.importo_centesimi,
                prenotazione_id=prenotazione.id, stato="completato",
                riferimento_provider=riferimento_rimborso,
            ))
            rimborsato += pagamento.importo_centesimi
        self._prenotazioni.aggiorna_stato(prenotazione.id, "annullata", in_utc(adesso), annullata_da)
        self._conn.commit()
        return rimborsato

    # --- Annullamenti da parte del salone ---

    def puo_annullare_salone(self, prenotazione: Prenotazione, adesso: datetime) -> bool:
        """
        Il salone annulla le prenotazioni confermate non ancora iniziate, senza il limite delle 2 ore.
        """
        return prenotazione.stato == "confermata" and prenotazione.inizio > in_utc(adesso)

    def _leggi_per_il_salone(self, prenotazione_id: int, utente: Utente, per_aggiornamento: bool = False):
        """
        Il proprietario legge qualsiasi prenotazione del proprio salone; un dipendente solo quelle
        della propria agenda. Il salone viene sempre dalla sessione (utente.salone_id), mai dall'URL.
        Raises: RisorsaNonTrovataError se non esiste, è di un altro salone o nell'agenda di un altro professionista.
        """
        if utente.salone_id is None:
            raise RisorsaNonTrovataError("Prenotazione non trovata.")
        dipendente_id = None if utente.ruolo == "proprietario" else utente.id
        prenotazione = self._prenotazioni.leggi_per_id(
            prenotazione_id, dipendente_id=dipendente_id, salone_id=utente.salone_id,
            per_aggiornamento=per_aggiornamento,
        )
        if prenotazione is None:
            raise RisorsaNonTrovataError("Prenotazione non trovata.")
        return prenotazione

    def prenotazione_per_il_salone(self, prenotazione_id: int, utente: Utente) -> Appuntamento:
        """
        Legge una prenotazione per la pagina di conferma dell'annullamento da parte del salone.
        Returns: l'Appuntamento con il cliente.
        Raises: RisorsaNonTrovataError come _leggi_per_il_salone.
        """
        prenotazione = self._leggi_per_il_salone(prenotazione_id, utente)
        return Appuntamento(prenotazione, self._utenti.leggi_per_id(prenotazione.cliente_id))

    def annulla_dal_salone(self, prenotazione_id: int, utente: Utente, adesso: datetime | None = None) -> int:
        """
        Annullamento da parte del salone (proprietario per tutti, dipendente per la propria agenda),
        con rimborso di quanto pagato online.
        Returns: l'importo rimborsato in centesimi.
        Raises: RisorsaNonTrovataError; AnnullamentoNonConsentitoError se non è confermata o è già iniziata.
        """
        adesso = adesso or datetime.now(UTC)
        prenotazione = self._leggi_per_il_salone(prenotazione_id, utente, per_aggiornamento=True)
        if not self.puo_annullare_salone(prenotazione, adesso):
            raise AnnullamentoNonConsentitoError(
                "Si possono annullare solo prenotazioni confermate e non ancora iniziate."
            )
        return self._annulla_con_rimborso(prenotazione, "salone", adesso)

    def agenda(self, dipendente_id: int, adesso: datetime | None = None) -> list[Appuntamento]:
        """
        Prossimi appuntamenti confermati di un professionista, dall'inizio di oggi (ora locale del suo salone).
        Returns: la lista degli Appuntamenti in ordine di inizio (vuota se non è un professionista).
        """
        adesso = adesso or datetime.now(UTC)
        dipendente = self._utenti.leggi_per_id(dipendente_id)
        if dipendente is None or dipendente.salone_id is None:
            return []
        fuso = self.disponibilita(dipendente.salone_id).fuso_orario
        inizio_oggi = datetime.combine(adesso.astimezone(fuso).date(), time(0), fuso)
        return [
            Appuntamento(prenotazione, self._utenti.leggi_per_id(prenotazione.cliente_id),
                         self.puo_annullare_salone(prenotazione, adesso))
            for prenotazione in self._prenotazioni.elenca_per_dipendente(dipendente_id, in_utc(inizio_oggi))
        ]

    def storico_professionista(self, dipendente_id: int, adesso: datetime | None = None) -> list[Appuntamento]:
        """
        Appuntamenti passati e prenotazioni annullate di un professionista, dalla più recente.
        Returns: la lista degli Appuntamenti.
        """
        adesso = adesso or datetime.now(UTC)
        return [
            Appuntamento(prenotazione, self._utenti.leggi_per_id(prenotazione.cliente_id))
            for prenotazione in self._prenotazioni.storico_per_dipendente(dipendente_id, in_utc(adesso))
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

from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ServizioPrenotato:
    """
    Servizio dentro una prenotazione, con durata e prezzo fissati al momento della prenotazione.
    """
    servizio_id: int
    nome: str
    durata_minuti: int
    prezzo_centesimi: int
    prenotazione_id: int | None = None

@dataclass
class Prenotazione:
    """
    Appuntamento di un cliente presso un dipendente, con i servizi scelti.
    """
    cliente_id: int
    dipendente_id: int
    inizio: datetime
    fine: datetime
    modalita_pagamento: str
    scade_il: datetime
    salone_id: int | None = None
    servizi: list[ServizioPrenotato] = field(default_factory=list) # ogni prenotazione riceve una lista nuova tutta sua invece di condividerne una con tutte le altre.
    stato: str = "in_attesa_pagamento"
    annullata_il: datetime | None = None
    annullata_da: str | None = None
    creato_il: datetime | None = None
    id: int | None = None

    def durata_totale(self) -> int:
        """
        Restituisce la durata della prenotazione in minuti, somma delle durate dei servizi.
        """
        return sum(s.durata_minuti for s in self.servizi)

    def prezzo_totale(self) -> int:
        """
        Restituisce il prezzo della prenotazione in centesimi, somma dei prezzi dei servizi.
        """
        return sum(s.prezzo_centesimi for s in self.servizi)
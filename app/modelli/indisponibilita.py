from dataclasses import dataclass
from datetime import datetime

@dataclass
class Indisponibilita:
    """
    Periodo senza prenotazioni: assenza di un dipendente o chiusura dell'intero salone.
    """
    inizio: datetime
    fine: datetime
    salone_id: int | None = None
    dipendente_id: int | None = None  # vuoto: chiusura dell'intero salone
    nota: str | None = None
    id: int | None = None
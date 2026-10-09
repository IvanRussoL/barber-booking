from dataclasses import dataclass
from datetime import datetime

@dataclass
class Indisponibilita:
    """
    Periodo senza prenotazioni: assenza di un dipendente o chiusura dell'intero magazzino.
    """
    inizio: datetime
    fine: datetime
    dipendente_id: int | None = None # Quando l'id dipendente è vuoto vuol dire che la chiusura è per l'intero magazzino.
    nota: str | None = None
    id: int | None = None
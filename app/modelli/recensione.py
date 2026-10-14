from dataclasses import dataclass
from datetime import datetime


@dataclass
class Recensione:
    """
    Giudizio di un cliente su un appuntamento svolto: voto da 1 a 5 e commento facoltativo.
    """
    prenotazione_id: int
    salone_id: int
    cliente_id: int
    voto: int
    commento: str | None = None
    autore: str | None = None  # nome e iniziale del cognome, letto insieme alla recensione (es. "Anna F.")
    creato_il: datetime | None = None
    id: int | None = None

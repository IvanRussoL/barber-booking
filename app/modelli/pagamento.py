from dataclasses import dataclass
from datetime import datetime

@dataclass
class Pagamento:
    """
    Movimento di denaro di una prenotazione o di un ordine: pagamento online, saldo in sede o rimborso.
    """
    tipo: str
    importo_centesimi: int
    # Prenotazione_id e ordine_id sono entrambi facoltativi: dei due ne va compilato esattamente uno.
    prenotazione_id: int | None = None
    ordine_id: int | None = None
    
    stato: str = "in_attesa"
    riferimento_provider: str | None = None
    creato_il: datetime | None = None
    id: int | None = None
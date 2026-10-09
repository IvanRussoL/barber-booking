from dataclasses import dataclass

@dataclass
class Servizio:
    """
    Servizio offerto dal salone, con durata e prezzo attuali.
    """
    nome:str
    durata_minuti: int
    prezzo_centesimi: int
    descrizione: str | None = None
    attivo: bool = True
    id: int | None = None
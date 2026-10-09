from dataclasses import dataclass

@dataclass
class Servizio:
    nome:str
    durata_minuti: int
    prezzo_centesimi: int
    descrizione: str | None = None
    attivo: bool = True
    id: int | None = None
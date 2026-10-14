from dataclasses import dataclass
from datetime import datetime

@dataclass
class Utente:
    """
    Persona che accede al sito: cliente, dipendente o proprietario.
    """
    email: str
    password_hash: str
    nome: str
    cognome: str
    telefono: str
    ruolo: str = "cliente"
    salone_id: int | None = None  # None per i clienti, il salone per dipendenti e proprietari
    riceve_prenotazioni: bool = False
    attivo: bool = True
    creato_il: datetime | None = None
    id: int | None = None
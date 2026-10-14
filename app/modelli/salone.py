from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Salone:
    """
    Un salone della piattaforma: dati pubblici, posizione e regole di prenotazione.
    Le regole (acconto, mesi prenotabili) le decide il proprietario del salone.
    """
    nome: str
    indirizzo: str
    provincia: str  # sigla, es. "NA"
    telefono: str
    latitudine: Decimal
    longitudine: Decimal
    percentuale_acconto: int = 30
    fuso_orario: str = "Europe/Rome"
    mesi_prenotabili: int = 3
    attivo: bool = True
    creato_il: datetime | None = None
    id: int | None = None


@dataclass
class Provincia:
    """
    Provincia italiana con la sua regione: serve a cercare i saloni per zona.
    """
    sigla: str
    nome: str
    regione: str

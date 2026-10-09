from dataclasses import dataclass
from decimal import Decimal

@dataclass
class Impostazioni:
    """
    Dati e regole configurabili del salone, modificabili solo dal proprietario.
    """
    nome_salone: str
    indirizzo: str
    telefono: str
    latitudine: Decimal
    longitudine: Decimal
    percentuale_acconto: int
    fuso_orario: str = "Europe/Rome"
    mesi_prenotabili: int = 3
    id: int = 1 # 1 poichè la riga in impostazioni e' sempre e solo una
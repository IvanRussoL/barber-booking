from dataclasses import dataclass, field
from datetime import date, time

@dataclass
class Turno:
    """
    Fascia oraria di apertura, nell'ora locale del salone.
    """
    ora_inizio = time
    ora_fine = time

@dataclass
class EccezioneData:
    """
    Data in cui non vale il calendario settimanale: salone chiuso o aperto con turni propri.
    """
    data: date
    aperto: bool
    turni: list[Turno] = field(default_factory=list)
    nota: str | None = None
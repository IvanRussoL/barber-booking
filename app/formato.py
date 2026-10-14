from datetime import UTC, datetime
from zoneinfo import ZoneInfo

GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]


def formatta_euro(centesimi: int) -> str:
    """
    Filtro Jinja "euro": trasforma i centesimi in un importo all'italiana (2550 -> "25,50 €").
    """
    euro, resto = divmod(centesimi, 100)
    return f"{euro},{resto:02d} €"


def formatta_durata(minuti: int) -> str:
    """
    Filtro Jinja "durata": 30 -> "30 min", 90 -> "1 h 30 min", 120 -> "2 h".
    """
    ore, resto = divmod(minuti, 60)
    if ore == 0:
        return f"{resto} min"
    return f"{ore} h {resto} min" if resto else f"{ore} h"


def formatta_data_ora(momento_utc: datetime, fuso_orario: ZoneInfo | str) -> str:
    """
    Filtro Jinja "data_ora": data e ora salvate in UTC mostrate nel fuso orario del salone
    (es. "mer 14/10/2026 09:30"). Il fuso orario può essere anche il suo nome, es. "Europe/Rome".
    """
    if isinstance(fuso_orario, str):
        fuso_orario = ZoneInfo(fuso_orario)
    locale = momento_utc.replace(tzinfo=UTC).astimezone(fuso_orario)
    return f"{GIORNI[locale.weekday()]} {locale:%d/%m/%Y %H:%M}"

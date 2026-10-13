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

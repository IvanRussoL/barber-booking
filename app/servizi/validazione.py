import re

from app.eccezioni import DatiNonValidiError


def testo_obbligatorio(valore: str, campo: str, lunghezza_massima: int) -> str:
    """
    Toglie gli spazi iniziali e finali e controlla che il testo non sia vuoto né troppo lungo.
    Returns: il testo ripulito.
    Raises: DatiNonValidiError se il testo è vuoto o supera la lunghezza massima.
    """
    valore = valore.strip()
    if not valore:
        raise DatiNonValidiError(f"Il campo {campo} è obbligatorio.")
    if len(valore) > lunghezza_massima:
        raise DatiNonValidiError(f"Il campo {campo} può avere al massimo {lunghezza_massima} caratteri.")
    return valore


def testo_facoltativo(valore: str, campo: str, lunghezza_massima: int) -> str | None:
    """
    Come testo_obbligatorio, ma un testo vuoto diventa None (NULL nel database).
    Returns: il testo ripulito, oppure None se è vuoto.
    Raises: DatiNonValidiError se supera la lunghezza massima.
    """
    if not valore.strip():
        return None
    return testo_obbligatorio(valore, campo, lunghezza_massima)


def euro_in_centesimi(valore: str, campo: str) -> int:
    """
    Converte un importo scritto in euro ("25", "25,50" o "25.50") in centesimi interi.
    Returns: l'importo in centesimi.
    Raises: DatiNonValidiError se non è un numero con al massimo due decimali.
    """
    valore = valore.strip()
    if not re.fullmatch(r"[0-9]{1,5}([.,][0-9]{1,2})?", valore):
        raise DatiNonValidiError(
            f"Il campo {campo} deve essere un importo in euro, ad esempio 25 o 25,50."
        )
    euro, _, decimali = valore.replace(",", ".").partition(".")
    return int(euro) * 100 + int(decimali.ljust(2, "0"))

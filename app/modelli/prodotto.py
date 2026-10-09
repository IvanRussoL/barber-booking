from dataclasses import dataclass

@dataclass
class Prodotto:
    """
    Prodotto in vendita nel salone, con prezzo attuale e disponibilità.
    """
    nome: str
    prezzo_centesimi: int
    descrizione: str | None = None
    foto: str | None = None # contiene solo il nome del file, l'immagine vera sta su disco.
    disponibile: bool = True # Ci dice se possiamo comprare il prodotto.
    attivo: bool = True # Attivo se compare nel catalogo.
    id: int | None = None